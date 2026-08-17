from __future__ import annotations

import base64
import io
import sys
import threading
import types
from pathlib import Path

from PIL import Image as PILImage

try:
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

from animated_images import normalize_image_bytes
from ex_public_source_feature import ExPublicSourceMixin


class _Harness(ExPublicSourceMixin):
    PUBLIC_SOURCE_SUBMISSION_MAX_SIZE = 10 * 1024 * 1024

    def _public_source_submission_payload(self, pig_id: str):
        return (
            {
                "id": pig_id,
                "name": "Pig",
                "description": "Animated EX",
                "analysis": "GIF public-source contract",
            },
            b"base-image",
        )


def _animated_gif_bytes() -> bytes:
    frames = [
        PILImage.new("RGBA", (20, 20), (20, 200, 80, 255)),
        PILImage.new("RGBA", (20, 20), (180, 30, 220, 255)),
    ]
    output = io.BytesIO()
    frames[0].save(
        output,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[90, 130],
        loop=1,
        disposal=2,
    )
    return output.getvalue()


def test_ex_public_source_payload_accepts_canonical_gif_variant(tmp_path: Path):
    harness = object.__new__(_Harness)
    harness._data_lock = threading.RLock()
    harness.local_ex_variant_image_dir = tmp_path
    harness._local_ex_variants = {
        "pig": {2: {"description": "GIF EX2", "image": "pig-ex2.gif"}}
    }
    raw = normalize_image_bytes(_animated_gif_bytes(), (512, 512))
    (tmp_path / "pig-ex2.gif").write_bytes(raw)

    record, base_raw, canonical, images = harness._ex_public_source_payload("pig")

    assert record["id"] == "pig"
    assert base_raw == b"base-image"
    assert canonical["pigs"]["pig"]["2"]["image"] == "pig-ex2.gif"
    assert [item["filename"] for item in images] == ["pig-ex2.gif"]
    decoded = base64.b64decode(images[0]["content"])
    with PILImage.open(io.BytesIO(decoded)) as image:
        assert image.is_animated
        assert image.n_frames == 2
