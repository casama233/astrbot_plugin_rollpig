from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from scripts.prepare_resource_catalog import CompatibilitySpec, merge_catalog


ROOT = Path(__file__).resolve().parents[1]
PINNED_COMMIT = "17ac1586a91c33995883803a55e2f755047f6e1f"


def _write_image(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (8, 8), (value, 80, 120, 255)).save(path)


def _write_catalog(root: Path, records: list[dict], *, image_dir: str) -> Path:
    root.mkdir(parents=True)
    (root / "pig.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for index, record in enumerate(records, start=1):
        _write_image(root / image_dir / f"{record['id']}.png", 30 + index)
    return root


def _compat_fixture(root: Path) -> tuple[Path, CompatibilitySpec]:
    records = [
        {
            "id": "shared-pig",
            "name": "舊共享豬",
            "description": "舊描述",
            "analysis": "舊文案",
        },
        {
            "id": "legacy-pig",
            "name": "舊版限定豬",
            "description": "切源前已存在",
            "analysis": "必須由兼容下限補回。",
        },
    ]
    compat = _write_catalog(root / "compat", records, image_dir="images")
    digest = hashlib.sha256((compat / "pig.json").read_bytes()).hexdigest()
    (compat / "manifest.json").write_text(
        json.dumps({"resource_version": "fixture-v1"}), encoding="utf-8"
    )
    spec = CompatibilitySpec(
        repository="fixture/repo",
        commit="deadbeef",
        resource_version="fixture-v1",
        pig_json_sha256=digest,
        sentinel_ids=("legacy-pig",),
    )
    return compat, spec


def test_merge_restores_missing_legacy_ids_and_keeps_current_overrides(tmp_path):
    primary_records = [
        {
            "id": "shared-pig",
            "name": "AstrBot 新共享豬",
            "description": "目前描述",
            "analysis": "目前文案優先。",
        },
        {
            "id": "astrbot-only",
            "name": "AstrBot 新豬",
            "description": "新來源新增",
            "analysis": "不能被舊快照覆蓋。",
        },
    ]
    primary = _write_catalog(tmp_path / "primary", primary_records, image_dir="image")
    primary_shared_bytes = (primary / "image" / "shared-pig.png").read_bytes()
    compat, spec = _compat_fixture(tmp_path)
    output = tmp_path / "merged"

    summary = merge_catalog(primary, compat, output, spec=spec)
    records = json.loads((output / "pig.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in records}

    assert set(by_id) == {"shared-pig", "legacy-pig", "astrbot-only"}
    assert by_id["shared-pig"]["name"] == "AstrBot 新共享豬"
    assert by_id["legacy-pig"]["name"] == "舊版限定豬"
    assert (output / "image" / "shared-pig.png").read_bytes() == primary_shared_bytes
    assert (output / "image" / "legacy-pig.png").is_file()
    assert summary["restored_ids"] == ["legacy-pig"]
    assert summary["merged_count"] == 3

    floor = json.loads((output / "compatibility_floor.json").read_text(encoding="utf-8"))
    assert set(floor["ids"]) == {"shared-pig", "legacy-pig"}
    assert floor["source_commit"] == "deadbeef"


def test_merge_rejects_mutated_frozen_snapshot(tmp_path):
    primary = _write_catalog(
        tmp_path / "primary",
        [
            {
                "id": "current-pig",
                "name": "目前豬",
                "description": "目前",
                "analysis": "目前來源。",
            }
        ],
        image_dir="image",
    )
    compat, spec = _compat_fixture(tmp_path)
    records = json.loads((compat / "pig.json").read_text(encoding="utf-8"))
    records[0]["name"] = "被偷偷修改"
    (compat / "pig.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    try:
        merge_catalog(primary, compat, tmp_path / "merged", spec=spec)
    except ValueError as exc:
        assert "指紋不符" in str(exc)
    else:  # pragma: no cover - protects the immutable snapshot contract
        raise AssertionError("mutated compatibility snapshot was accepted")


def test_workflow_pins_the_exact_pre_cutover_commit_and_checks_sentinels():
    workflow = (ROOT / ".github" / "workflows" / "resource-source.yml").read_text(
        encoding="utf-8"
    )
    helper = (ROOT / "scripts" / "prepare_resource_catalog.py").read_text(
        encoding="utf-8"
    )
    assert PINNED_COMMIT in workflow
    assert PINNED_COMMIT in helper
    assert "miku-pig" in workflow
    assert "wechat-pig" in workflow
    assert "duke-pig" in workflow
    assert "compatibility_floor.json" in workflow
