from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
legacy_path = ROOT / "legacy_main.py"
text = legacy_path.read_text(encoding="utf-8")

# 1. Runtime validator import for atomic cloud-sync validation.
old = "    from .rollpig_core import consecutive_duplicate_day_streak\n"
new = (
    "    from .ex_variants import validate_ex_variants\n"
    "    from .rollpig_core import consecutive_duplicate_day_streak\n"
)
if old not in text:
    raise RuntimeError("relative import anchor not found")
text = text.replace(old, new, 1)
old = "    from rollpig_core import consecutive_duplicate_day_streak\n"
new = (
    "    from ex_variants import validate_ex_variants\n"
    "    from rollpig_core import consecutive_duplicate_day_streak\n"
)
if old not in text:
    raise RuntimeError("fallback import anchor not found")
text = text.replace(old, new, 1)

# 2. Resource count budget.
old = "    RESOURCE_MAX_IMAGES = 500\n"
new = "    RESOURCE_MAX_IMAGES = 500\n    RESOURCE_MAX_VARIANT_IMAGES = 1000\n"
if old not in text:
    raise RuntimeError("resource image constant anchor not found")
text = text.replace(old, new, 1)

# 3. A same-version snapshot created by an older plugin must be supplemented
# when the manifest already advertises EX resources.
old = '''                    if (\n                        not force\n                        and version == self._cloud_state().get("resource_version")\n                        and self._load_cloud_pigs()\n                    ):\n'''
new = '''                    if (\n                        not force\n                        and version == self._cloud_state().get("resource_version")\n                        and self._load_cloud_pigs()\n                        and (\n                            not isinstance(manifest.get("ex_variants"), dict)\n                            or (\n                                self.resource_active_dir / "pig_ex_variants.json"\n                            ).is_file()\n                        )\n                    ):\n'''
if old not in text:
    raise RuntimeError("same-version sync anchor not found")
text = text.replace(old, new, 1)

# 4. Replace the manifest payload download/validation section with a v1-compatible
# optional EX extension. Core pig/image behavior is intentionally kept identical.
start_marker = '                    pig_meta = manifest.get("pig_json")\n'
end_marker = "\n\n                if previous.exists():\n"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise RuntimeError("resource sync block anchors not found")
block = '''                    pig_meta = manifest.get("pig_json")\n                    image_metas = manifest.get("images")\n                    ex_meta = manifest.get("ex_variants")\n                    variant_image_metas = manifest.get("variant_images", [])\n                    if not isinstance(pig_meta, dict):\n                        raise ValueError("manifest 缺少 pig_json")\n                    if not isinstance(image_metas, list):\n                        raise ValueError("manifest 缺少 images")\n                    if len(image_metas) > self.RESOURCE_MAX_IMAGES:\n                        raise ValueError("云资源图片数量超过 500")\n                    if ex_meta is not None and not isinstance(ex_meta, dict):\n                        raise ValueError("manifest ex_variants 必须是对象")\n                    if not isinstance(variant_image_metas, list):\n                        raise ValueError("manifest variant_images 必须是数组")\n                    if ex_meta is None and variant_image_metas:\n                        raise ValueError("manifest 缺少 ex_variants，却声明了差分图片")\n                    if len(variant_image_metas) > self.RESOURCE_MAX_VARIANT_IMAGES:\n                        raise ValueError("EX 差分图片数量超过 1000")\n                    declared_total = int(pig_meta.get("size") or 0) + sum(\n                        int(meta.get("size") or 0)\n                        for meta in image_metas\n                        if isinstance(meta, dict)\n                    )\n                    if isinstance(ex_meta, dict):\n                        declared_total += int(ex_meta.get("size") or 0)\n                        declared_total += sum(\n                            int(meta.get("size") or 0)\n                            for meta in variant_image_metas\n                            if isinstance(meta, dict)\n                        )\n                    if declared_total > self.RESOURCE_PACKAGE_MAX_SIZE:\n                        raise ValueError("云资源包声明大小超过 128 MiB")\n                    pig_raw = await self._download_manifest_item(\n                        client,\n                        self.resource_manifest_url,\n                        pig_meta,\n                        min(self.resource_max_file_size, 2 * 1024 * 1024),\n                    )\n                    pigs = self._validate_pig_records(\n                        json.loads(pig_raw.decode("utf-8-sig"))\n                    )\n                    pig_ids = {item["id"] for item in pigs}\n                    ex_raw = b""\n                    normalized_ex: dict[str, dict[int, dict[str, str]]] = {}\n                    if isinstance(ex_meta, dict):\n                        ex_raw = await self._download_manifest_item(\n                            client,\n                            self.resource_manifest_url,\n                            ex_meta,\n                            min(self.resource_max_file_size, 2 * 1024 * 1024),\n                        )\n                        normalized_ex = validate_ex_variants(\n                            json.loads(ex_raw.decode("utf-8-sig")),\n                            pig_ids,\n                            image_extensions=set(self.IMAGE_EXTENSIONS),\n                        )\n                    staging_images = staging / "images"\n                    staging_images.mkdir(parents=True, exist_ok=True)\n                    (staging / "pig.json").write_bytes(pig_raw)\n                    staging_variants = staging / "ex_variants"\n                    if isinstance(ex_meta, dict):\n                        staging_variants.mkdir(parents=True, exist_ok=True)\n                        (staging / "pig_ex_variants.json").write_bytes(ex_raw)\n                    # 公共包接近两百张图；较低并发对慢速反代和家庭网络更稳定。\n                    semaphore = asyncio.Semaphore(4)\n                    budget_lock = asyncio.Lock()\n                    package_total = len(pig_raw) + len(ex_raw)\n\n                    async def fetch_base_image(meta):\n                        nonlocal package_total\n                        if not isinstance(meta, dict):\n                            raise ValueError("manifest 图片条目无效")\n                        filename = str(meta.get("filename") or "")\n                        if (\n                            Path(filename).name != filename\n                            or Path(filename).suffix.lower().lstrip(".")\n                            not in self.IMAGE_EXTENSIONS\n                            or not re.fullmatch(\n                                r"[a-z0-9][a-z0-9_-]{0,63}",\n                                Path(filename).stem,\n                            )\n                        ):\n                            raise ValueError(f"图片文件名无效：{filename}")\n                        async with semaphore:\n                            data = await self._download_manifest_item(\n                                client,\n                                self.resource_manifest_url,\n                                meta,\n                                self.resource_max_file_size,\n                            )\n                        async with budget_lock:\n                            package_total += len(data)\n                            if package_total > self.RESOURCE_PACKAGE_MAX_SIZE:\n                                raise ValueError("云资源包总大小超过 128 MiB")\n                        return filename, data\n\n                    async def fetch_variant_image(meta):\n                        nonlocal package_total\n                        if not isinstance(meta, dict):\n                            raise ValueError("manifest EX 差分图片条目无效")\n                        filename = str(meta.get("filename") or "")\n                        if (\n                            Path(filename).name != filename\n                            or Path(filename).suffix.lower().lstrip(".")\n                            not in self.IMAGE_EXTENSIONS\n                            or not re.fullmatch(\n                                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", filename\n                            )\n                        ):\n                            raise ValueError(f"EX 差分图片文件名无效：{filename}")\n                        async with semaphore:\n                            data = await self._download_manifest_item(\n                                client,\n                                self.resource_manifest_url,\n                                meta,\n                                self.resource_max_file_size,\n                            )\n                        async with budget_lock:\n                            package_total += len(data)\n                            if package_total > self.RESOURCE_PACKAGE_MAX_SIZE:\n                                raise ValueError("云资源包总大小超过 128 MiB")\n                        return filename, data\n\n                    async def fetch_and_store_base(meta):\n                        filename, data = await fetch_base_image(meta)\n                        self._validate_image_dimensions(data, filename)\n                        await asyncio.to_thread(\n                            (staging_images / filename).write_bytes, data\n                        )\n                        return filename\n\n                    async def fetch_and_store_variant(meta):\n                        filename, data = await fetch_variant_image(meta)\n                        self._validate_image_dimensions(data, filename)\n                        await asyncio.to_thread(\n                            (staging_variants / filename).write_bytes, data\n                        )\n                        return filename\n\n                    tasks = [\n                        asyncio.create_task(fetch_and_store_base(meta))\n                        for meta in image_metas\n                    ]\n                    filenames: list[str] = []\n                    try:\n                        for task in asyncio.as_completed(tasks):\n                            filenames.append(await task)\n                    except Exception:\n                        for task in tasks:\n                            task.cancel()\n                        await asyncio.gather(*tasks, return_exceptions=True)\n                        raise\n                    if len(filenames) != len(set(filenames)):\n                        raise ValueError("云资源 manifest 存在重复图片文件名")\n                    image_ids = {Path(name).stem for name in filenames}\n                    missing = pig_ids.difference(image_ids)\n                    if missing:\n                        raise ValueError(\n                            f"云资源缺少图片：{', '.join(sorted(missing)[:10])}"\n                        )\n\n                    variant_tasks = [\n                        asyncio.create_task(fetch_and_store_variant(meta))\n                        for meta in variant_image_metas\n                    ]\n                    variant_filenames: list[str] = []\n                    try:\n                        for task in asyncio.as_completed(variant_tasks):\n                            variant_filenames.append(await task)\n                    except Exception:\n                        for task in variant_tasks:\n                            task.cancel()\n                        await asyncio.gather(*variant_tasks, return_exceptions=True)\n                        raise\n                    if len(variant_filenames) != len(set(variant_filenames)):\n                        raise ValueError("云资源 manifest 存在重复 EX 差分图片文件名")\n                    if isinstance(ex_meta, dict):\n                        declared_variant_images = {\n                            str(item.get("image") or "")\n                            for levels in normalized_ex.values()\n                            for item in levels.values()\n                            if str(item.get("image") or "")\n                        }\n                        fetched_variant_images = set(variant_filenames)\n                        missing_variant = declared_variant_images.difference(\n                            fetched_variant_images\n                        )\n                        extra_variant = fetched_variant_images.difference(\n                            declared_variant_images\n                        )\n                        if missing_variant:\n                            raise ValueError(\n                                "云资源缺少 EX 差分图片："\n                                + ", ".join(sorted(missing_variant)[:10])\n                            )\n                        if extra_variant:\n                            raise ValueError(\n                                "云资源存在未引用 EX 差分图片："\n                                + ", ".join(sorted(extra_variant)[:10])\n                            )\n'''
text = text[:start] + block + text[end:]

# 5. Image resolution: administrator local images keep absolute priority, then
# current EX art, then normal cloud/bundled base art.
start_marker = "    def find_image_file(self, pig_id: str) -> Path | None:\n"
end_marker = "\n    def render_pig_image(self, pig_data: dict) -> Path | None:\n"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise RuntimeError("find_image_file block anchors not found")
find_block = '''    def find_image_file(\n        self, pig_id: str, ex_level: int | None = None\n    ) -> Path | None:\n        """Resolve local override, optional EX art, cloud base, then bundled base."""\n        for ext in self.IMAGE_EXTENSIONS:\n            local = self.custom_image_dir / f"{pig_id}.{ext}"\n            if local.exists():\n                logger.debug(f"找到的小猪图片文件：{local.absolute()}")\n                return local\n        if ex_level:\n            resolver = getattr(self, "_ex_variant_image_path", None)\n            if callable(resolver):\n                variant = resolver(str(pig_id), max(0, int(ex_level)))\n                if variant and variant.exists():\n                    logger.debug(f"找到 EX 差分图片：{variant.absolute()}")\n                    return variant\n        for directory in (self.resource_active_dir / "images", self.image_dir):\n            for ext in self.IMAGE_EXTENSIONS:\n                file = directory / f"{pig_id}.{ext}"\n                if file.exists():\n                    logger.debug(f"找到的小猪图片文件：{file.absolute()}")\n                    return file\n        logger.warning(f"未找到小猪ID {pig_id} 对应的图片文件")\n        return None\n'''
text = text[:start] + find_block + text[end:]

# 6. Decorated pig dictionaries carry _ex_level. Passing it is harmless for
# random/search/admin cards (they simply have no marker and stay on base art).
old = "        avatar_path = self.find_image_file(pig_id)\n"
new = '''        avatar_path = self.find_image_file(\n            pig_id, ex_level=int(pig_data.get("_ex_level", 0) or 0)\n        )\n'''
count = text.count(old)
if count != 2:
    raise RuntimeError(f"expected 2 pig_data avatar lookups, found {count}")
text = text.replace(old, new)

old = '            image_path = self.find_image_file(pig_id)\n'
new = '''            image_path = self.find_image_file(\n                pig_id,\n                ex_level=(\n                    max(0, int(unlocked[pig_id].get("count", 1)) - 1)\n                    if is_unlocked\n                    else 0\n                ),\n            )\n'''
if old not in text:
    raise RuntimeError("pigsty image lookup anchor not found")
text = text.replace(old, new, 1)

old = '            path = self.find_image_file(str(pig.get("id") or ""))\n'
new = '''            path = self.find_image_file(\n                str(pig.get("id") or ""),\n                ex_level=int(pig.get("_ex_level", 0) or 0),\n            )\n'''
count = text.count(old)
if count < 3:
    raise RuntimeError(f"expected at least 3 pig dictionary image lookups, found {count}")
text = text.replace(old, new)

legacy_path.write_text(text, encoding="utf-8")
