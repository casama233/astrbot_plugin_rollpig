from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"patch anchor not found: {label}")
    return text.replace(old, new, 1)


path = Path("ex_admin_feature.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''try:
    from .ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants
''',
    '''try:
    from .animated_images import (
        image_extension_from_bytes,
        image_mime_type_from_bytes,
        normalize_image_bytes,
    )
    from .ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import (
        image_extension_from_bytes,
        image_mime_type_from_bytes,
        normalize_image_bytes,
    )
    from ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants
''',
    "EX admin image imports",
)
text = replace_once(
    text,
    '''    def _write_local_ex_image(self, filename: str, data: bytes) -> None:
        root = self.local_ex_variant_image_dir
        if not isinstance(root, Path):
            raise ValueError("本地 EX 图片目录尚未初始化")
        if len(data) > self.LOCAL_EX_IMAGE_MAX_SIZE:
            raise ValueError("EX 图片超过 10MB")
        root.mkdir(parents=True, exist_ok=True)
        target = root / filename
        with tempfile.NamedTemporaryFile(dir=root, delete=False, suffix=".tmp") as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
''',
    '''    def _normalise_local_ex_upload(self, encoded: str) -> bytes:
        value = str(encoded or "").strip()
        if not value:
            raise ValueError("EX 图片内容为空")
        if "," in value:
            value = value.split(",", 1)[1]
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValueError("EX 图片不是有效 Base64") from exc
        if not raw or len(raw) > self.LOCAL_EX_IMAGE_MAX_SIZE:
            raise ValueError("EX 图片为空或超过 10MB")
        normalized = normalize_image_bytes(raw, (512, 512))
        if not normalized or len(normalized) > self.LOCAL_EX_IMAGE_MAX_SIZE:
            raise ValueError("正規化后的 EX 图片超过 10MB")
        return normalized

    def _write_local_ex_image(self, filename: str, data: bytes) -> None:
        root = self.local_ex_variant_image_dir
        if not isinstance(root, Path):
            raise ValueError("本地 EX 图片目录尚未初始化")
        if len(data) > self.LOCAL_EX_IMAGE_MAX_SIZE:
            raise ValueError("EX 图片超过 10MB")
        extension = image_extension_from_bytes(data)
        if extension not in {"png", "gif"} or Path(filename).suffix.lower() != f".{extension}":
            raise ValueError("EX 图片副档名与实际格式不一致")
        root.mkdir(parents=True, exist_ok=True)
        target = root / filename
        with tempfile.NamedTemporaryFile(dir=root, delete=False, suffix=".tmp") as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
''',
    "EX admin local image writer",
)
text = replace_once(
    text,
    '''            image_content = str(payload.get("image") or "")
            normalized_image = None
            if image_content:
                normalized_image = await asyncio.to_thread(
                    self._normalise_uploaded_image, image_content
                )
                if len(normalized_image) > self.LOCAL_EX_IMAGE_MAX_SIZE:
                    raise ValueError("EX 图片超过 10MB")
''',
    '''            image_content = str(payload.get("image") or "")
            normalized_image = None
            if image_content:
                normalized_image = await asyncio.to_thread(
                    self._normalise_local_ex_upload, image_content
                )
''',
    "EX admin upload normalization",
)
text = replace_once(
    text,
    '''                filename = f"{pig_id}-ex{level}.png"
                if normalized_image is not None:
                    self._write_local_ex_image(filename, normalized_image)
                    item["image"] = filename
                elif payload.get("remove_image") is True:
                    item.pop("image", None)

                if item:
                    levels[level] = item
                else:
                    levels.pop(level, None)
                if not levels:
                    variants.pop(pig_id, None)

                self._persist_local_ex_state(variants)
                if payload.get("remove_image") is True and normalized_image is None:
                    root = self.local_ex_variant_image_dir
                    if isinstance(root, Path):
                        try:
                            (root / filename).unlink(missing_ok=True)
                        except OSError as exc:
                            logger.warning(f"清理未引用 EX 图片失败：{exc}")
''',
    '''                previous_image = str(item.get("image") or "")
                image_to_remove = ""
                if normalized_image is not None:
                    extension = image_extension_from_bytes(normalized_image)
                    if extension not in {"png", "gif"}:
                        raise ValueError("EX 图片格式无效")
                    filename = f"{pig_id}-ex{level}.{extension}"
                    self._write_local_ex_image(filename, normalized_image)
                    item["image"] = filename
                    if previous_image and previous_image != filename:
                        image_to_remove = previous_image
                elif payload.get("remove_image") is True:
                    image_to_remove = previous_image
                    item.pop("image", None)

                if item:
                    levels[level] = item
                else:
                    levels.pop(level, None)
                if not levels:
                    variants.pop(pig_id, None)

                self._persist_local_ex_state(variants)
                if image_to_remove:
                    root = self.local_ex_variant_image_dir
                    if isinstance(root, Path):
                        try:
                            (root / image_to_remove).unlink(missing_ok=True)
                        except OSError as exc:
                            logger.warning(f"清理未引用 EX 图片失败：{exc}")
''',
    "EX admin dynamic filename",
)
text = replace_once(
    text,
    '''                        "mime_type": "image/png",
                        "base64": base64.b64encode(raw).decode("ascii"),
''',
    '''                        "mime_type": image_mime_type_from_bytes(raw),
                        "base64": base64.b64encode(raw).decode("ascii"),
''',
    "EX admin preview mime",
)
path.write_text(text, encoding="utf-8")

path = Path("ex_public_source_feature.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''try:
    from .ex_variants import serialize_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import serialize_ex_variants
''',
    '''try:
    from .animated_images import image_mime_type_from_bytes
    from .ex_variants import serialize_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import image_mime_type_from_bytes
    from ex_variants import serialize_ex_variants
''',
    "EX public image imports",
)
text = replace_once(
    text,
    '''            expected = f"{pig_id}-ex{int(level)}.png"
            if image != expected:
                raise ValueError(
                    f"EX Lv.{level} 图片文件名不是标准投稿格式：应为 {expected}"
                )
''',
    '''            expected = {
                f"{pig_id}-ex{int(level)}.png",
                f"{pig_id}-ex{int(level)}.gif",
            }
            if image not in expected:
                raise ValueError(
                    f"EX Lv.{level} 图片文件名不是标准投稿格式：应为 PNG 或 GIF canonical 文件名"
                )
''',
    "EX public canonical filename",
)
text = replace_once(
    text,
    '        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}-ex[1-5]\\.png", filename):\n',
    '        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}-ex[1-5]\\.(?:png|gif)", filename):\n',
    "EX public review filename regex",
)
text = replace_once(
    text,
    '''        return {
            "mime_type": "image/png",
            "base64": base64.b64encode(raw).decode("ascii"),
        }
''',
    '''        return {
            "mime_type": image_mime_type_from_bytes(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }
''',
    "EX public review mime",
)
path.write_text(text, encoding="utf-8")

path = Path("tests/test_ex_admin_feature.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''import json
import sys
import threading
import types
from pathlib import Path
''',
    '''import base64
import io
import json
import sys
import threading
import types
from pathlib import Path

from PIL import Image as PILImage
''',
    "EX admin test imports",
)
text += '''


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
'''
path.write_text(text, encoding="utf-8")

Path("tests/test_ex_public_source_gif.py").write_text('''from __future__ import annotations

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
''', encoding="utf-8")
