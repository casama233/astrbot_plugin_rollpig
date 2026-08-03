from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8")
old = '''    def _persist_catalog_override(
        self, record: dict, normalized_image: bytes | None
    ) -> None:
        pig_id = str(record.get("id") or "")
        with self._data_lock:
            if getattr(self.storage, "supports_domain_writes", False):
                self.storage.upsert_catalog_override(record=dict(record))
            else:
                overrides = self._validate_pig_records(
                    self.load_json(self.local_overrides_path, [])
                )
                override_index = next(
                    (
                        i
                        for i, item in enumerate(overrides)
                        if str(item.get("id")) == pig_id
                    ),
                    None,
                )
                if override_index is None:
                    overrides.append(dict(record))
                else:
                    overrides[override_index] = dict(record)
                tombstones = {
                    str(item) for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.discard(pig_id)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
            if normalized_image:
                self._write_custom_image(pig_id, normalized_image)
            self._reload_catalog_layers()

    def _persist_catalog_delete(self, pig_id: str) -> None:
        with self._data_lock:
            if getattr(self.storage, "supports_domain_writes", False):
                self.storage.delete_catalog_entry(pig_id=str(pig_id))
            else:
                overrides = [
                    dict(item)
                    for item in self.load_json(self.local_overrides_path, [])
                    if str(item.get("id")) != pig_id
                ]
                tombstones = {
                    str(item) for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.add(pig_id)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
            for ext in self.IMAGE_EXTENSIONS:
                (self.custom_image_dir / f"{pig_id}.{ext}").unlink(missing_ok=True)
            self._reload_catalog_layers()
'''
new = '''    def _snapshot_custom_images(self, pig_id: str) -> dict[str, bytes]:
        """Capture the current custom-image set for compensating rollback."""
        snapshots: dict[str, bytes] = {}
        for ext in self.IMAGE_EXTENSIONS:
            image_path = self.custom_image_dir / f"{pig_id}.{ext}"
            if image_path.exists():
                snapshots[ext] = image_path.read_bytes()
        return snapshots

    def _restore_custom_images(self, pig_id: str, snapshots: dict[str, bytes]) -> None:
        """Restore an image snapshot after a metadata transaction fails."""
        for ext in self.IMAGE_EXTENSIONS:
            (self.custom_image_dir / f"{pig_id}.{ext}").unlink(missing_ok=True)
        for ext, data in snapshots.items():
            target = self.custom_image_dir / f"{pig_id}.{ext}"
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=self.custom_image_dir,
                prefix=f".{pig_id}.",
                suffix=".restore.tmp",
                delete=False,
            ) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            tmp_path.replace(target)

    def _persist_catalog_override(
        self, record: dict, normalized_image: bytes | None
    ) -> None:
        pig_id = str(record.get("id") or "")
        with self._data_lock:
            previous_images = (
                self._snapshot_custom_images(pig_id) if normalized_image else {}
            )
            if normalized_image:
                self._write_custom_image(pig_id, normalized_image)
            try:
                if getattr(self.storage, "supports_domain_writes", False):
                    self.storage.upsert_catalog_override(record=dict(record))
                else:
                    overrides = self._validate_pig_records(
                        self.load_json(self.local_overrides_path, [])
                    )
                    override_index = next(
                        (
                            i
                            for i, item in enumerate(overrides)
                            if str(item.get("id")) == pig_id
                        ),
                        None,
                    )
                    if override_index is None:
                        overrides.append(dict(record))
                    else:
                        overrides[override_index] = dict(record)
                    tombstones = {
                        str(item) for item in self.load_json(self.tombstones_path, [])
                    }
                    tombstones.discard(pig_id)
                    self.save_json_batch(
                        {
                            self.local_overrides_path: overrides,
                            self.tombstones_path: sorted(tombstones),
                        }
                    )
            except Exception:
                if normalized_image:
                    self._restore_custom_images(pig_id, previous_images)
                raise
            self._reload_catalog_layers()

    def _persist_catalog_delete(self, pig_id: str) -> None:
        with self._data_lock:
            previous_images = self._snapshot_custom_images(pig_id)
            for ext in self.IMAGE_EXTENSIONS:
                (self.custom_image_dir / f"{pig_id}.{ext}").unlink(missing_ok=True)
            try:
                if getattr(self.storage, "supports_domain_writes", False):
                    self.storage.delete_catalog_entry(pig_id=str(pig_id))
                else:
                    overrides = [
                        dict(item)
                        for item in self.load_json(self.local_overrides_path, [])
                        if str(item.get("id")) != pig_id
                    ]
                    tombstones = {
                        str(item) for item in self.load_json(self.tombstones_path, [])
                    }
                    tombstones.add(pig_id)
                    self.save_json_batch(
                        {
                            self.local_overrides_path: overrides,
                            self.tombstones_path: sorted(tombstones),
                        }
                    )
            except Exception:
                self._restore_custom_images(pig_id, previous_images)
                raise
            self._reload_catalog_layers()
'''
if text.count(old) != 1:
    raise RuntimeError(f"catalog persistence anchor count={text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

regression = Path("tests/test_source_regressions.py")
tests = regression.read_text(encoding="utf-8")
addition = '''\n\ndef test_catalog_image_changes_are_compensated_on_metadata_failure():\n    save = ast.get_source_segment(SOURCE, _method("_persist_catalog_override")) or ""\n    delete = ast.get_source_segment(SOURCE, _method("_persist_catalog_delete")) or ""\n    assert save.index("_write_custom_image") < save.index("upsert_catalog_override")\n    assert "except Exception:" in save\n    assert "_restore_custom_images" in save\n    assert delete.index("unlink") < delete.index("delete_catalog_entry")\n    assert "_restore_custom_images" in delete\n'''
if "test_catalog_image_changes_are_compensated_on_metadata_failure" not in tests:
    regression.write_text(tests + addition, encoding="utf-8")
