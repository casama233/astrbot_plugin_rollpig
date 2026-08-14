from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable


VariantResolver = Callable[[str, int], Path | None]


def _directory_signature(directory: Path) -> tuple[str, int, int]:
    """Return a cheap cache identity that changes when directory entries change."""
    directory = Path(directory)
    try:
        stat = directory.stat()
        return str(directory), int(stat.st_mtime_ns), int(stat.st_ctime_ns)
    except OSError:
        return str(directory), -1, -1


@lru_cache(maxsize=4096)
def _find_in_directory_cached(
    directory_value: str,
    mtime_ns: int,
    ctime_ns: int,
    pig_id: str,
    image_extensions: tuple[str, ...],
) -> Path | None:
    """Resolve one base image while the containing directory is unchanged."""
    del mtime_ns, ctime_ns  # cache-key only
    directory = Path(directory_value)
    for ext in image_extensions:
        candidate = directory / f"{pig_id}.{ext}"
        if candidate.exists():
            return candidate
    return None


@dataclass(frozen=True)
class ResourceReadService:
    """Resolve effective pig image paths without owning synchronization or writes."""

    image_extensions: tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "gif")

    def _find_cached(self, directory: Path, pig_id: str) -> Path | None:
        directory_value, mtime_ns, ctime_ns = _directory_signature(directory)
        return _find_in_directory_cached(
            directory_value,
            mtime_ns,
            ctime_ns,
            pig_id,
            self.image_extensions,
        )

    def clear_cache(self) -> None:
        """Drop memoized path probes after an explicit resource maintenance action."""
        _find_in_directory_cached.cache_clear()

    def find_image(
        self,
        pig_id: str,
        *,
        custom_image_dir: Path,
        cloud_image_dir: Path,
        bundled_image_dir: Path,
        ex_level: int | None = None,
        variant_resolver: VariantResolver | None = None,
    ) -> Path | None:
        """Preserve the established read precedence.

        local override -> optional EX variant -> cloud base -> bundled base
        """
        pig_id = str(pig_id)
        local = self._find_cached(custom_image_dir, pig_id)
        if local is not None:
            return local

        # Variant resolution remains live because the callback can depend on EX
        # state outside these three base-image directories.
        if ex_level and callable(variant_resolver):
            variant = variant_resolver(pig_id, max(0, int(ex_level)))
            if variant and variant.exists():
                return variant

        for directory in (cloud_image_dir, bundled_image_dir):
            candidate = self._find_cached(directory, pig_id)
            if candidate is not None:
                return candidate
        return None
