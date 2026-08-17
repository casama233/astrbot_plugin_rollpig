from __future__ import annotations

import base64
import io
import json
import sys
import threading
import types
from pathlib import Path

from PIL import Image as PILImage

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
from ex_variant_feature import ExVariantMixin


BASE = {
    "id": "pig",
    "name": "猪",
    "description": "基础描述",
    "analysis": "基础完整文案",
}


class _Context:
    def __init__(self):
        self.routes = []

    def register_web_api(self, path, handler, methods, description):
        self.routes.append((path, tuple(methods), description, handler.__name__))


class _Base:
    IMAGE_EXTENSIONS = ("png", "gif", "webp", "jpg", "jpeg")
    PLUGIN_NAME = "astrbot_plugin_rollpig_plus"

    def __init__(self, context, config):
        self.plugin_data_dir = Path(config["data"])
        self.res_dir = Path(config["bundled"])
        self.resource_active_dir = Path(config["active"])
        self.local_overrides_path = self.plugin_data_dir / "local_overrides.json"
        self.pig_list = [dict(BASE)]
        self.collections = {"u1": {"pigs": {"pig": {"count": 3}}}}
        self._data_lock = threading.RLock()
        self.context = context

    def load_json(self, path, default):
        path = Path(path)
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, path, data):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _runtime_document(self, key, path, default):
        del key
        return self.load_json(path, default)

    def _get_user_collection(self, user_id):
        return self.collections.get(str(user_id), {})

    def _find_catalog_pig(self, pig_id):
        return dict(BASE) if str(pig_id) == "pig" else None

    def _reload_catalog_layers(self):
        return None


class _Harness(ExAdminMixin, ExVariantMixin, _Base):
    pass


def _write_upstream(root: Path, description: str = "内建 EX1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pig_ex_variants.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pigs": {"pig": {"1": {"description": description}}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _make(tmp_path: Path) -> _Harness:
    data = tmp_path / "data"
    bundled = tmp_path / "bundled"
    active = tmp_path / "active"
    data.mkdir()
    active.mkdir()
    _write_upstream(bundled)
    context = _Context()
    return _Harness(
        context,
        {"data": data, "bundled": bundled, "active": active},
    )


def test_admin_mixin_registers_separate_ex_management_api(tmp_path):
    harness = _make(tmp_path)
    paths = {item[0] for item in harness.context.routes}
    assert f"/{harness.PLUGIN_NAME}/ex/variants" in paths
    assert f"/{harness.PLUGIN_NAME}/ex/variants/save" in paths
    assert f"/{harness.PLUGIN_NAME}/ex/variants/delete" in paths
    assert f"/{harness.PLUGIN_NAME}/ex/variants/image" in paths


def test_local_base_override_blocks_upstream_until_local_ex_exists(tmp_path):
    harness = _make(tmp_path)
    harness.local_overrides_path.write_text(
        json.dumps([{"id": "pig", "name": "本地猪", "description": "本地基础", "analysis": "本地文案"}], ensure_ascii=False),
        encoding="utf-8",
    )

    blocked = harness._decorate_ex_variant(BASE, "u1")
    assert blocked["_ex_level"] == 2
    assert blocked["description"] == "基础描述"
    assert blocked.get("_ex_variant_level", 0) == 0

    harness._persist_local_ex_state(
        {"pig": {1: {"description": "本地 EX1"}, 2: {"analysis": "本地 EX2 文案"}}}
    )
    local = harness._decorate_ex_variant(BASE, "u1")
    assert local["_ex_level"] == 2
    assert local["_ex_variant_level"] == 2
    assert local["description"] == "本地 EX1"
    assert local["analysis"] == "本地 EX2 文案"

    preview = harness._effective_ex_preview(BASE, 2)
    assert preview["source"] == "local"
    assert preview["description"] == "本地 EX1"
    assert preview["analysis"] == "本地 EX2 文案"


def test_local_ex_has_priority_over_cloud_and_can_own_its_image(tmp_path):
    harness = _make(tmp_path)
    _write_upstream(harness.resource_active_dir, "云端 EX1")
    harness._reload_ex_variants()
    assert harness._ex_variant_source == "cloud"
    assert harness._decorate_ex_variant(BASE, "u1")["description"] == "云端 EX1"

    image_root = harness.local_ex_variant_image_dir
    assert image_root is not None
    (image_root / "pig-ex2.png").write_bytes(b"png")
    harness._persist_local_ex_state(
        {
            "pig": {
                1: {"description": "本地 EX1"},
                2: {"image": "pig-ex2.png"},
            }
        }
    )

    decorated = harness._decorate_ex_variant(BASE, "u1")
    assert decorated["description"] == "本地 EX1"
    assert decorated["_ex_image"] == "pig-ex2.png"
    assert harness._ex_variant_image_path("pig", 2) == image_root / "pig-ex2.png"


def test_local_ex_persistence_is_canonical_and_snapshot_reports_effective_levels(tmp_path):
    harness = _make(tmp_path)
    harness._persist_local_ex_state(
        {"pig": {3: {"description": "EX3"}, 1: {"analysis": "EX1 文案"}}}
    )

    payload = json.loads(harness.local_ex_variants_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert list(payload["pigs"]["pig"]) == ["1", "3"]

    snapshot = harness._admin_ex_snapshot()
    assert snapshot["local_variant_pigs"] == 1
    assert snapshot["local_variant_levels"] == 2
    item = snapshot["items"][0]
    assert item["local_levels"]["1"]["analysis"] == "EX1 文案"
    assert len(item["effective"]) == 5
    assert item["effective"][4]["description"] == "EX3"
    assert item["effective"][4]["analysis"] == "EX1 文案"



def _animated_gif_bytes() -> bytes:
    frames = [
        PILImage.new("RGBA", (24, 16), (255, 0, 0, 255)),
        PILImage.new("RGBA", (24, 16), (0, 0, 255, 255)),
    ]
    output = io.BytesIO()
    frames[0].save(
        output,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[80, 140],
        loop=2,
        disposal=2,
    )
    return output.getvalue()


def test_local_ex_upload_preserves_animated_gif_and_dynamic_mime(tmp_path):
    harness = _make(tmp_path)
    encoded = base64.b64encode(_animated_gif_bytes()).decode("ascii")
    normalized = harness._normalise_local_ex_upload(encoded)
    image_root = harness.local_ex_variant_image_dir
    assert image_root is not None
    harness._write_local_ex_image("pig-ex2.gif", normalized)
    harness._persist_local_ex_state({"pig": {2: {"image": "pig-ex2.gif"}}})

    target = image_root / "pig-ex2.gif"
    assert target.is_file()
    with PILImage.open(target) as image:
        assert image.is_animated
        assert image.n_frames == 2
        assert image.size == (512, 512)
        assert image.info.get("loop") == 2
    assert harness._ex_variant_image_path("pig", 2) == target
