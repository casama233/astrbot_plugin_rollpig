from pathlib import Path


def test_legacy_main_delegates_claim_resolution_and_ownership_merge():
    source = Path("legacy_main.py").read_text(encoding="utf-8")

    assert "self.collection_service = CollectionService()" in source
    assert "self.collection_service.claimed_read_candidates(" in source
    assert "self.collection_service.merge_ownership(" in source
    assert "storage.get_user_collection((candidate,))" in source


def test_identity_boundary_does_not_restore_the_rejected_direct_sum_merge():
    service = Path("services/collection_service.py").read_text(encoding="utf-8")
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")
    sqlite = Path("storage/sqlite_storage.py").read_text(encoding="utf-8")

    assert "merge_user_collections" not in service
    assert "merge_user_collections" not in legacy
    assert "merge_user_collections" not in sqlite
    assert 'current["count"] = max(' in service
    assert 'merged["duplicate_streak"]' not in service


def test_collection_service_is_storage_and_astrbot_independent():
    source = Path("services/collection_service.py").read_text(encoding="utf-8")

    forbidden = (
        "astrbot",
        "sqlite3",
        "StorageBackend",
        "event.send",
        "save_json",
        "load_json",
    )
    for token in forbidden:
        assert token not in source
