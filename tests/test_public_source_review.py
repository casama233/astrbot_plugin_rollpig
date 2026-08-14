from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from PIL import Image

from scripts.build_resource_source import build_source
from source_service.app import APIError, ReviewApplication, ServiceConfig


def _png(path: Path, color: tuple[int, int, int, int]) -> bytes:
    Image.new("RGBA", (32, 32), color).save(path)
    return path.read_bytes()


def _application(tmp_path: Path) -> ReviewApplication:
    publish = tmp_path / "public"
    catalog = publish / "catalog"
    (catalog / "image").mkdir(parents=True)
    (catalog / "pig.json").write_text(
        json.dumps(
            [
                {
                    "id": "base-pig",
                    "name": "基礎豬",
                    "description": "公共來源",
                    "analysis": "既有公共資源。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _png(catalog / "image" / "base-pig.png", (255, 100, 120, 255))
    release = publish / "releases" / "2026.08.14.1"
    build_source(
        catalog,
        release,
        "2026.08.14.1",
        generated_at="2026-08-14T00:00:00+00:00",
    )
    os.symlink("releases/2026.08.14.1", publish / "v1")
    token = tmp_path / "admin.token"
    token.write_text("a" * 48, encoding="utf-8")
    return ReviewApplication(
        ServiceConfig(
            state_root=tmp_path / "state",
            catalog_root=catalog,
            publish_root=publish,
            admin_token_file=token,
        )
    )


def test_public_source_submission_approval_publishes_atomic_v1(tmp_path):
    app = _application(tmp_path)
    upload = tmp_path / "upload.png"
    image = _png(upload, (100, 170, 255, 255))
    result = app.submit(
        {
            "record": {
                "id": "community-pig",
                "name": "社群豬",
                "description": "等待審核",
                "analysis": "批准後應進入我們自己的公共豬源。",
            },
            "image": base64.b64encode(image).decode("ascii"),
        },
        source_address="203.0.113.10",
        client_version="3.5.0",
    )
    submission_id = result["submission_id"]
    pending = app.list_submissions("pending")
    assert [item["submission_id"] for item in pending] == [submission_id]
    assert app.image_path(submission_id).is_file()

    reviewed = app.review(submission_id, "approve", "內容與圖片通過")
    assert reviewed["status"] == "approved"
    assert reviewed["resource_version"].startswith("2026.")
    current = (app.config.publish_root / "v1").resolve()
    manifest = json.loads((current / "manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads((current / "pig.json").read_text(encoding="utf-8"))
    assert manifest["pig_count"] == 2
    assert {item["id"] for item in catalog} == {"base-pig", "community-pig"}
    assert (current / "images" / "community-pig.png").is_file()
    assert app.list_submissions("pending") == []
    assert app.list_submissions("approved")[0]["resource_version"] == reviewed[
        "resource_version"
    ]


def test_public_source_rejects_existing_catalog_id(tmp_path):
    app = _application(tmp_path)
    upload = tmp_path / "upload.png"
    image = _png(upload, (20, 30, 40, 255))
    try:
        app.submit(
            {
                "record": {
                    "id": "base-pig",
                    "name": "重複豬",
                    "description": "重複",
                    "analysis": "不應進入待審核隊列。",
                },
                "image": base64.b64encode(image).decode("ascii"),
            },
            source_address="203.0.113.11",
            client_version="3.5.0",
        )
    except APIError as exc:
        assert exc.status == 409
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("duplicate source ID was accepted")



def test_public_source_submission_reject_mutates_pending_without_publishing(tmp_path):
    app = _application(tmp_path)
    upload = tmp_path / "reject.png"
    image = _png(upload, (90, 80, 70, 255))
    result = app.submit(
        {
            "record": {
                "id": "rejected-pig",
                "name": "被拒绝的小猪",
                "description": "不应发布",
                "analysis": "拒绝操作必须真正把 pending 改为 rejected。",
            },
            "image": base64.b64encode(image).decode("ascii"),
        },
        source_address="203.0.113.12",
        client_version="3.6.5",
    )
    submission_id = result["submission_id"]
    before = (app.config.publish_root / "v1").resolve()

    reviewed = app.review(submission_id, "reject", "内容不符合公共源要求")

    assert reviewed["status"] == "rejected"
    assert app.list_submissions("pending") == []
    rejected = app.list_submissions("rejected")
    assert rejected[0]["submission_id"] == submission_id
    assert rejected[0]["reviewer_note"] == "内容不符合公共源要求"
    assert (app.config.publish_root / "v1").resolve() == before
    current_catalog = json.loads((before / "pig.json").read_text(encoding="utf-8"))
    assert "rejected-pig" not in {item["id"] for item in current_catalog}
