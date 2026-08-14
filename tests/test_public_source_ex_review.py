from __future__ import annotations

import base64
import json
import os
from http import HTTPStatus
from pathlib import Path

import pytest
from PIL import Image

from scripts.build_resource_source import build_source
from source_service.app import APIError, ServiceConfig
from source_service.app_v2 import ReviewApplicationV2


def _png(path: Path, color: tuple[int, int, int, int]) -> bytes:
    Image.new("RGBA", (48, 48), color).save(path)
    return path.read_bytes()


def _application(tmp_path: Path) -> ReviewApplicationV2:
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
    release = publish / "releases" / "2026.08.15.1"
    build_source(
        catalog,
        release,
        "2026.08.15.1",
        generated_at="2026-08-15T00:00:00+00:00",
    )
    os.symlink("releases/2026.08.15.1", publish / "v1")
    token = tmp_path / "admin.token"
    token.write_text("a" * 48, encoding="utf-8")
    return ReviewApplicationV2(
        ServiceConfig(
            state_root=tmp_path / "state",
            catalog_root=catalog,
            publish_root=publish,
            admin_token_file=token,
        )
    )


def _base_payload(tmp_path: Path, pig_id: str = "community-pig") -> dict:
    image = _png(tmp_path / f"{pig_id}.png", (100, 170, 255, 255))
    return {
        "record": {
            "id": pig_id,
            "name": "社群豬",
            "description": "等待審核",
            "analysis": "批准後應進入我們自己的公共豬源。",
        },
        "image": base64.b64encode(image).decode("ascii"),
    }


def test_v1_submission_remains_legacy_compatible(tmp_path):
    app = _application(tmp_path)
    result = app.submit(
        _base_payload(tmp_path),
        source_address="203.0.113.10",
        client_version="3.7.1",
    )
    submission_id = result["submission_id"]

    pending = app.list_submissions("pending")[0]
    assert pending["submission_id"] == submission_id
    assert pending["submission_version"] == 1
    assert pending["ex_variant_levels"] == 0
    assert pending["variant_images"] == []

    approved = app.review(submission_id, "approve", "legacy still works")
    assert approved["status"] == "approved"
    catalog = json.loads(
        (app.config.catalog_root / "pig.json").read_text(encoding="utf-8")
    )
    assert any(item["id"] == "community-pig" for item in catalog)


def test_v2_text_only_ex_is_reviewed_and_published_atomically(tmp_path):
    app = _application(tmp_path)
    payload = _base_payload(tmp_path)
    payload.update(
        {
            "submission_version": 2,
            "ex_variants": {
                "schema_version": 1,
                "pigs": {
                    "community-pig": {
                        "1": {"description": "EX1 已養熟"},
                        "3": {"analysis": "EX3 的完整成長文案。"},
                    }
                },
            },
            "variant_images": [],
        }
    )

    result = app.submit(
        payload,
        source_address="203.0.113.11",
        client_version="3.7.2",
    )
    assert result["submission_version"] == 2
    assert result["ex_variant_levels"] == 2

    pending = app.list_submissions("pending")[0]
    assert pending["submission_version"] == 2
    assert pending["ex_variant_levels"] == 2
    assert pending["ex_variants"]["pigs"]["community-pig"]["1"]["description"] == "EX1 已養熟"

    approved = app.review(result["submission_id"], "approve", "EX copy approved")
    assert approved["status"] == "approved"
    ex_catalog = json.loads(
        (app.config.catalog_root / "pig_ex_variants.json").read_text(encoding="utf-8")
    )
    assert ex_catalog["pigs"]["community-pig"]["1"]["description"] == "EX1 已養熟"
    assert ex_catalog["pigs"]["community-pig"]["3"]["analysis"] == "EX3 的完整成長文案。"

    current = app.config.publish_root / "v1"
    manifest = json.loads((current / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ex_variants"]["path"] == "pig_ex_variants.json"


def test_v2_variant_image_is_normalized_reviewable_and_published(tmp_path):
    app = _application(tmp_path)
    payload = _base_payload(tmp_path, "image-pig")
    raw_variant = _png(tmp_path / "variant-source.png", (80, 220, 140, 255))
    payload.update(
        {
            "submission_version": 2,
            "ex_variants": {
                "schema_version": 1,
                "pigs": {
                    "image-pig": {
                        "2": {
                            "description": "EX2 換圖",
                            "image": "image-pig-ex2.png",
                        }
                    }
                },
            },
            "variant_images": [
                {
                    "filename": "image-pig-ex2.png",
                    "content": base64.b64encode(raw_variant).decode("ascii"),
                }
            ],
        }
    )

    result = app.submit(
        payload,
        source_address="203.0.113.12",
        client_version="3.7.2",
    )
    submission_id = result["submission_id"]
    review_image = app.variant_image_path(submission_id, "image-pig-ex2.png")
    assert review_image.is_file()
    with Image.open(review_image) as image:
        assert image.size == (512, 512)
        assert image.format == "PNG"

    pending = app.list_submissions("pending")[0]
    assert pending["variant_images"] == ["image-pig-ex2.png"]

    app.review(submission_id, "approve", "EX art approved")
    published = app.config.catalog_root / "ex_variants" / "image-pig-ex2.png"
    assert published.is_file()
    with Image.open(published) as image:
        assert image.size == (512, 512)

    manifest = json.loads(
        (app.config.publish_root / "v1" / "manifest.json").read_text(encoding="utf-8")
    )
    assert "image-pig-ex2.png" in manifest["variant_images"]


def test_v2_reject_keeps_catalog_and_public_release_unchanged(tmp_path):
    app = _application(tmp_path)
    before_link = os.readlink(app.config.publish_root / "v1")
    payload = _base_payload(tmp_path, "rejected-pig")
    payload.update(
        {
            "submission_version": 2,
            "ex_variants": {
                "schema_version": 1,
                "pigs": {"rejected-pig": {"1": {"description": "不要發布"}}},
            },
            "variant_images": [],
        }
    )
    result = app.submit(
        payload,
        source_address="203.0.113.13",
        client_version="3.7.2",
    )
    reviewed = app.review(result["submission_id"], "reject", "not approved")
    assert reviewed["status"] == "rejected"
    assert os.readlink(app.config.publish_root / "v1") == before_link
    records = json.loads(
        (app.config.catalog_root / "pig.json").read_text(encoding="utf-8")
    )
    assert not any(item["id"] == "rejected-pig" for item in records)


def test_v2_rejects_missing_or_unreferenced_variant_images_before_queueing(tmp_path):
    app = _application(tmp_path)
    payload = _base_payload(tmp_path, "bad-ex-pig")
    payload.update(
        {
            "submission_version": 2,
            "ex_variants": {
                "schema_version": 1,
                "pigs": {
                    "bad-ex-pig": {
                        "1": {"image": "bad-ex-pig-ex1.png"}
                    }
                },
            },
            "variant_images": [],
        }
    )
    with pytest.raises(APIError) as exc:
        app.submit(
            payload,
            source_address="203.0.113.14",
            client_version="3.7.2",
        )
    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert app.list_submissions("pending") == []
