#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "legacy_main.py"
source = PATH.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected one match, found {count}: {old[:80]!r}")
    source = source.replace(old, new, 1)


replace_once(
    "from .services import DrawService, RoastService",
    "from .services import CatalogService, DrawService, ResourceReadService, RoastService",
)
replace_once(
    "from services import DrawService, RoastService",
    "from services import CatalogService, DrawService, ResourceReadService, RoastService",
)
replace_once(
    "        self.roast_service = RoastService()\n",
    "        self.catalog_service = CatalogService(page_size=self.CATALOG_PAGE_SIZE)\n"
    "        self.resource_read_service = ResourceReadService(\n"
    "            image_extensions=tuple(self.IMAGE_EXTENSIONS)\n"
    "        )\n"
    "        self.roast_service = RoastService()\n",
)

old_merge = '''        override_map = {item["id"]: item for item in overrides}\n        merged: list[dict] = []\n        used: set[str] = set()\n        for item in base:\n            pig_id = item["id"]\n            if pig_id in tombstones:\n                continue\n            merged.append(dict(override_map.get(pig_id, item)))\n            used.add(pig_id)\n        for item in overrides:\n            if item["id"] not in used and item["id"] not in tombstones:\n                merged.append(dict(item))\n        self.pig_list = merged\n'''
new_merge = '''        self.pig_list = self.catalog_service.merge_layers(\n            base, overrides, tombstones\n        )\n'''
replace_once(old_merge, new_merge)

replace_once(
    '''    def _find_catalog_pig(self, pig_id: str) -> dict | None:\n        return next(\n            (pig for pig in self.pig_list if str(pig.get("id")) == pig_id),\n            None,\n        )\n''',
    '''    def _find_catalog_pig(self, pig_id: str) -> dict | None:\n        pig = self.catalog_service.find(self.pig_list, pig_id)\n        return pig if isinstance(pig, dict) else None\n''',
)

old_image = '''    def find_image_file(\n        self, pig_id: str, ex_level: int | None = None\n    ) -> Path | None:\n        """Resolve local override, optional EX art, cloud base, then bundled base."""\n        for ext in self.IMAGE_EXTENSIONS:\n            local = self.custom_image_dir / f"{pig_id}.{ext}"\n            if local.exists():\n                logger.debug(f"找到的小猪图片文件：{local.absolute()}")\n                return local\n        if ex_level:\n            resolver = getattr(self, "_ex_variant_image_path", None)\n            if callable(resolver):\n                variant = resolver(str(pig_id), max(0, int(ex_level)))\n                if variant and variant.exists():\n                    logger.debug(f"找到 EX 差分图片：{variant.absolute()}")\n                    return variant\n        for directory in (self.resource_active_dir / "images", self.image_dir):\n            for ext in self.IMAGE_EXTENSIONS:\n                file = directory / f"{pig_id}.{ext}"\n                if file.exists():\n                    logger.debug(f"找到的小猪图片文件：{file.absolute()}")\n                    return file\n        logger.warning(f"未找到小猪ID {pig_id} 对应的图片文件")\n        return None\n'''
new_image = '''    def find_image_file(\n        self, pig_id: str, ex_level: int | None = None\n    ) -> Path | None:\n        """Resolve the effective image through the resource read boundary."""\n        resolver = getattr(self, "_ex_variant_image_path", None)\n        path = self.resource_read_service.find_image(\n            pig_id,\n            custom_image_dir=self.custom_image_dir,\n            cloud_image_dir=self.resource_active_dir / "images",\n            bundled_image_dir=self.image_dir,\n            ex_level=ex_level,\n            variant_resolver=resolver if callable(resolver) else None,\n        )\n        if path:\n            logger.debug(f"找到的小猪图片文件：{path.absolute()}")\n            return path\n        logger.warning(f"未找到小猪ID {pig_id} 对应的图片文件")\n        return None\n'''
replace_once(old_image, new_image)

replace_once(
    '''    def _ordered_pigsty_pigs(self, unlocked: dict) -> list[dict]:\n        """按解锁状态分区，且不改变每个分区内的管理员图鉴顺序。"""\n        unlocked_ids = set(unlocked) if isinstance(unlocked, dict) else set()\n        return [\n            pig for pig in self.pig_list if str(pig.get("id") or "") in unlocked_ids\n        ] + [\n            pig\n            for pig in self.pig_list\n            if str(pig.get("id") or "") not in unlocked_ids\n        ]\n''',
    '''    def _ordered_pigsty_pigs(self, unlocked: dict) -> list[dict]:\n        """按解锁状态分区，且不改变每个分区内的管理员图鉴顺序。"""\n        return [\n            pig\n            for pig in self.catalog_service.ordered_for_collection(\n                self.pig_list, unlocked\n            )\n            if isinstance(pig, dict)\n        ]\n''',
)

source = source.replace(
    "max(1, math.ceil(len(self.pig_list) / self.CATALOG_PAGE_SIZE))",
    "self.catalog_service.page_count(self.pig_list)",
)
replace_once(
    "        pigs = random.sample(self.pig_list, min(amount, len(self.pig_list)))\n",
    "        pigs = self.catalog_service.sample(self.pig_list, amount)\n",
)
old_search = '''        matches = [\n            pig\n            for pig in self.pig_list\n            if query\n            in " ".join(\n                str(pig.get(key, ""))\n                for key in ("id", "name", "description", "analysis")\n            ).lower()\n        ]\n'''
replace_once(
    old_search,
    "        matches = self.catalog_service.search(self.pig_list, query)\n",
)

PATH.write_text(source, encoding="utf-8")
print("wired CatalogService and ResourceReadService into legacy_main.py")
