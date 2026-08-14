from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


VariantResolver = Callable[[str, int], Path | None]


@dataclass(frozen=True)
class ResourceReadService:
    """Resolve effective pig image paths without owning synchronization or writes."""

    image_extensions: tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "gif")

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
        for ext in self.image_extensions:
            local = custom_image_dir / f"{pig_id}.{ext}"
            if local.exists():
                return local

        if ex_level and callable(variant_resolver):
            variant = variant_resolver(pig_id, max(0, int(ex_level)))
            if variant and variant.exists():
                return variant

        for directory in (cloud_image_dir, bundled_image_dir):
            for ext in self.image_extensions:
                candidate = directory / f"{pig_id}.{ext}"
                if candidate.exists():
                    return candidate
        return None
