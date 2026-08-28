from __future__ import annotations

import base64
import sys
import types
from pathlib import Path

try:  # Unit tests do not need a running AstrBot web server.
    import astrbot.api  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )
    web_module = types.ModuleType("astrbot.api.web")
    web_module.request = types.SimpleNamespace()
    astrbot_module.api = api_module
    sys.modules.setdefault("astrbot", astrbot_module)
    sys.modules.setdefault("astrbot.api", api_module)
    sys.modules.setdefault("astrbot.api.web", web_module)

from ex_admin_feature import ExAdminMixin


BASE = {
    "id": "pig",
    "name": "猪",
    "description": "基础描述",
    "analysis": "基础完整文案",
}


def _preview_harness(tmp_path: Path) -> ExAdminMixin:
    harness = object.__new__(ExAdminMixin)
    local_root = tmp_path / "local"
    public_root = tmp_path / "public"
    local_root.mkdir()
    public_root.mkdir()
    base_path = tmp_path / "pig.png"
    base_path.write_bytes(b"base")

    harness._local_ex_variants = {}
    harness.local_ex_variant_image_dir = local_root
    harness._ex_variants = {}
    harness._ex_variant_image_root = public_root
    harness._ex_variant_source = "bundled"
    harness._find_catalog_pig = (
        lambda pig_id: dict(BASE) if pig_id == "pig" else None
    )
    harness._has_local_pig_override = lambda pig_id: False
    harness.find_image_file = (
        lambda pig_id, ex_level=None: base_path if pig_id == "pig" else None
    )
    return harness


def test_effective_preview_inherits_local_image_and_simulates_remove(
    tmp_path: Path,
):
    harness = _preview_harness(tmp_path)
    local_root = harness.local_ex_variant_image_dir
    assert isinstance(local_root, Path)
    local_image = local_root / "pig-ex1.png"
    local_image.write_bytes(b"local")
    harness._local_ex_variants = {
        "pig": {
            1: {"image": "pig-ex1.png"},
            2: {"description": "本地 EX2"},
        }
    }

    path, source, level = harness._effective_ex_image_preview_path("pig", 2)
    assert path == local_image
    assert source == "local"
    assert level == 1

    path, source, level = harness._effective_ex_image_preview_path(
        "pig", 1, remove_local_image=True
    )
    assert path == tmp_path / "pig.png"
    assert source == "base"
    assert level == 0


def test_effective_preview_restores_public_image_when_last_local_image_is_removed(
    tmp_path: Path,
):
    harness = _preview_harness(tmp_path)
    local_root = harness.local_ex_variant_image_dir
    public_root = harness._ex_variant_image_root
    assert isinstance(local_root, Path)
    assert isinstance(public_root, Path)
    (local_root / "pig-ex1.png").write_bytes(b"local")
    public_image = public_root / "pig-public-ex1.png"
    public_image.write_bytes(b"public")

    harness._local_ex_variants = {"pig": {1: {"image": "pig-ex1.png"}}}
    harness._ex_variants = {
        "pig": {
            1: {"image": "pig-public-ex1.png", "description": "公共 EX1"}
        }
    }
    harness._ex_variant_source = "cloud"

    path, source, level = harness._effective_ex_image_preview_path(
        "pig", 1, remove_local_image=True
    )
    assert path == public_image
    assert source == "cloud"
    assert level == 1


def test_ex_card_preview_delegates_to_runtime_renderer_and_cleans_temp_file(tmp_path: Path):
    harness = _preview_harness(tmp_path)
    harness._ex_variants = {
        "pig": {2: {"description": "EX2 描述", "analysis": "EX2 完整文案"}}
    }
    harness._ex_variant_source = "bundled"
    rendered = tmp_path / "rendered.png"
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    seen = {}

    def render(display):
        seen.clear()
        seen.update(display)
        rendered.write_bytes(png)
        return rendered

    harness.render_pig_image = render
    harness.EX_CARD_PREVIEW_MAX_SIZE = 64 * 1024 * 1024

    payload = harness._render_ex_card_preview_payload("pig", 2)
    assert seen["_ex_level"] == 2
    assert seen["description"] == "EX2 描述"
    assert seen["analysis"] == "EX2 完整文案"
    assert payload["mime_type"] == "image/png"
    assert base64.b64decode(payload["base64"]) == png
    assert not rendered.exists()

    payload = harness._render_ex_card_preview_payload("pig", 2, base=True)
    assert seen["_ex_level"] == 0
    assert seen["description"] == BASE["description"]
    assert seen["analysis"] == BASE["analysis"]
    assert payload["source"] == "base"
    assert not rendered.exists()


def test_ex_editor_previews_exact_runtime_cards_instead_of_fake_browser_cards():
    source = Path("pages/pig-manager/ex-integration-core.js").read_text(
        encoding="utf-8"
    )
    assert "ex/variants/card" in source
    assert "data-effective-card-image" in source
    assert "data-base-card-image" in source
    assert "真实发送 renderer" in source
    assert "effective: true" in source
    assert "base: true" in source
    assert "FileReader" in source
    assert "ex-preview-card-effective" in source
    assert "data-compare-toggle" in source
    assert '<div class="chat-body">' not in source
    assert "data-effective-image" not in source
