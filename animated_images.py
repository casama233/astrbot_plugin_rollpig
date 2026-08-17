from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageOps


ANIMATED_GIF_MAX_FRAMES = 240
ANIMATED_GIF_MAX_DURATION_MS = 60_000
ANIMATED_GIF_MIN_FRAME_DURATION_MS = 20
ANIMATED_GIF_MAX_SOURCE_PIXELS = 25_000_000
ANIMATED_GIF_MAX_SOURCE_EDGE = 8192


@dataclass(frozen=True)
class AnimatedGifFrames:
    frames: tuple[PILImage.Image, ...]
    durations: tuple[int, ...]
    loop: int


def _safe_duration(value: object) -> int:
    try:
        duration = int(value or 0)
    except (TypeError, ValueError):
        duration = 0
    return max(ANIMATED_GIF_MIN_FRAME_DURATION_MS, duration or 100)


def _validate_source_geometry(source: PILImage.Image) -> None:
    width, height = source.size
    if (
        width <= 0
        or height <= 0
        or width > ANIMATED_GIF_MAX_SOURCE_EDGE
        or height > ANIMATED_GIF_MAX_SOURCE_EDGE
        or width * height > ANIMATED_GIF_MAX_SOURCE_PIXELS
    ):
        raise ValueError("图片尺寸过大，最高支持 8192×8192")


def image_mime_type_from_bytes(raw: bytes) -> str:
    try:
        with PILImage.open(io.BytesIO(raw)) as source:
            fmt = str(source.format or "").upper()
    except Exception:
        return "application/octet-stream"
    return {
        "GIF": "image/gif",
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "WEBP": "image/webp",
    }.get(fmt, "application/octet-stream")


def image_extension_from_bytes(raw: bytes) -> str:
    mime = image_mime_type_from_bytes(raw)
    return {
        "image/gif": "gif",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }.get(mime, "bin")


def is_animated_gif_bytes(raw: bytes) -> bool:
    try:
        with PILImage.open(io.BytesIO(raw)) as source:
            return (
                str(source.format or "").upper() == "GIF"
                and bool(getattr(source, "is_animated", False))
                and int(getattr(source, "n_frames", 1) or 1) > 1
            )
    except Exception:
        return False


def is_animated_gif_path(path: Path) -> bool:
    try:
        with PILImage.open(Path(path)) as source:
            return (
                str(source.format or "").upper() == "GIF"
                and bool(getattr(source, "is_animated", False))
                and int(getattr(source, "n_frames", 1) or 1) > 1
            )
    except Exception:
        return False


def load_fitted_gif_frames(
    source_or_path: bytes | bytearray | Path,
    size: tuple[int, int],
) -> AnimatedGifFrames:
    if isinstance(source_or_path, (bytes, bytearray)):
        source_ctx = io.BytesIO(bytes(source_or_path))
    else:
        source_ctx = Path(source_or_path)

    width, height = (max(1, int(size[0])), max(1, int(size[1])))
    with PILImage.open(source_ctx) as source:
        if str(source.format or "").upper() != "GIF":
            raise ValueError("图片不是 GIF")
        frame_count = int(getattr(source, "n_frames", 1) or 1)
        if frame_count <= 1:
            raise ValueError("GIF 不是动画")
        if frame_count > ANIMATED_GIF_MAX_FRAMES:
            raise ValueError(
                f"GIF 帧数过多，最多支持 {ANIMATED_GIF_MAX_FRAMES} 帧"
            )
        _validate_source_geometry(source)
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        loop = max(0, int(source.info.get("loop", 0) or 0))
        frames: list[PILImage.Image] = []
        durations: list[int] = []
        total_duration = 0
        for index in range(frame_count):
            source.seek(index)
            _validate_source_geometry(source)
            duration = _safe_duration(source.info.get("duration", 100))
            total_duration += duration
            if total_duration > ANIMATED_GIF_MAX_DURATION_MS:
                raise ValueError(
                    f"GIF 动画时长过长，最多支持 {ANIMATED_GIF_MAX_DURATION_MS // 1000} 秒"
                )
            frame = source.convert("RGBA")
            frame = ImageOps.fit(frame, (width, height), method=method)
            frames.append(frame)
            durations.append(duration)
        return AnimatedGifFrames(tuple(frames), tuple(durations), loop)


def save_animated_gif_bytes(
    frames: tuple[PILImage.Image, ...] | list[PILImage.Image],
    durations: tuple[int, ...] | list[int],
    *,
    loop: int = 0,
) -> bytes:
    if not frames:
        raise ValueError("GIF 没有可保存的帧")
    output = io.BytesIO()
    normalized_durations = [
        _safe_duration(durations[index] if index < len(durations) else 100)
        for index in range(len(frames))
    ]
    first = frames[0].convert("RGBA")
    rest = [frame.convert("RGBA") for frame in frames[1:]]
    first.save(
        output,
        "GIF",
        save_all=True,
        append_images=rest,
        duration=normalized_durations,
        loop=max(0, int(loop)),
        disposal=2,
        optimize=True,
    )
    return output.getvalue()


def normalize_image_bytes(raw: bytes, size: tuple[int, int] = (512, 512)) -> bytes:
    """Normalize still images to PNG while preserving animated GIFs as GIFs."""
    if not raw:
        raise ValueError("图片文件为空")
    try:
        with PILImage.open(io.BytesIO(raw)) as source:
            source.verify()
        with PILImage.open(io.BytesIO(raw)) as source:
            _validate_source_geometry(source)
            animated = (
                str(source.format or "").upper() == "GIF"
                and bool(getattr(source, "is_animated", False))
                and int(getattr(source, "n_frames", 1) or 1) > 1
            )
            if not animated:
                method = getattr(PILImage, "Resampling", PILImage).LANCZOS
                normalized = ImageOps.fit(
                    ImageOps.exif_transpose(source).convert("RGBA"),
                    size,
                    method,
                )
                output = io.BytesIO()
                normalized.save(output, "PNG", optimize=True)
                return output.getvalue()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("无法读取图片，请上传 PNG/JPG/WEBP/GIF") from exc

    animation = load_fitted_gif_frames(raw, size)
    return save_animated_gif_bytes(
        animation.frames,
        animation.durations,
        loop=animation.loop,
    )
