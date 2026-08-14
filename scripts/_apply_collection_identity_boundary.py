from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
legacy_path = ROOT / "legacy_main.py"
source = legacy_path.read_text(encoding="utf-8")

old_import = "from .services import CatalogService, DrawService, ResourceReadService, RoastService"
new_import = "from .services import CatalogService, CollectionService, DrawService, ResourceReadService, RoastService"
if old_import not in source:
    raise SystemExit("relative services import marker not found")
source = source.replace(old_import, new_import, 1)

old_direct_import = "from services import CatalogService, DrawService, ResourceReadService, RoastService"
new_direct_import = "from services import CatalogService, CollectionService, DrawService, ResourceReadService, RoastService"
if old_direct_import not in source:
    raise SystemExit("direct services import marker not found")
source = source.replace(old_direct_import, new_direct_import, 1)

old_ctor = """        self.catalog_service = CatalogService(page_size=self.CATALOG_PAGE_SIZE)\n        self.resource_read_service = ResourceReadService(\n"""
new_ctor = """        self.catalog_service = CatalogService(page_size=self.CATALOG_PAGE_SIZE)\n        self.collection_service = CollectionService()\n        self.resource_read_service = ResourceReadService(\n"""
if old_ctor not in source:
    raise SystemExit("service constructor marker not found")
source = source.replace(old_ctor, new_ctor, 1)

old_candidates = '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:\n        """Return only identity keys that belong to the current platform claim."""\n        candidates = self._identity_candidates(str(user_id))\n        if len(candidates) == 1:\n            return candidates\n        namespaced = candidates[0]\n        storage_key = self._storage_user_key(namespaced)\n        return tuple(dict.fromkeys((namespaced, storage_key)))\n'''
new_candidates = '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:\n        """Return only identity fragments proven to belong to this logical user."""\n        candidates = self._identity_candidates(str(user_id))\n        if len(candidates) == 1:\n            return candidates\n        namespaced = candidates[0]\n        storage_key = self._storage_user_key(namespaced)\n        claims_root = getattr(self, "history", {}).get("identity_claims", {})\n        user_claims = (\n            claims_root.get("users", {})\n            if isinstance(claims_root, dict)\n            else {}\n        )\n        return self.collection_service.claimed_read_candidates(\n            candidates,\n            user_claims,\n            preferred_storage_key=storage_key,\n        )\n'''
if old_candidates not in source:
    raise SystemExit("_user_read_candidates marker not found")
source = source.replace(old_candidates, new_candidates, 1)

old_collection = '''    def _get_user_collection(self, user_id: str) -> dict:\n        candidates = tuple(self._user_read_candidates(str(user_id)))\n        if getattr(self.storage, "supports_domain_reads", False):\n            stored = self.storage.get_user_collection(candidates)\n            return stored or {}\n        users = self.history.get("users", {})\n        for candidate in candidates:\n            user = users.get(candidate, {})\n            if isinstance(user, dict) and user:\n                return user\n        return {}\n'''
new_collection = '''    def _get_user_collection(self, user_id: str) -> dict:\n        candidates = tuple(self._user_read_candidates(str(user_id)))\n        fragments: list[dict] = []\n        if getattr(self.storage, "supports_domain_reads", False):\n            for candidate in candidates:\n                stored = self.storage.get_user_collection((candidate,))\n                if isinstance(stored, dict) and stored:\n                    fragments.append(stored)\n            return self.collection_service.merge_ownership(fragments)\n        users = self.history.get("users", {})\n        for candidate in candidates:\n            user = users.get(candidate, {})\n            if isinstance(user, dict) and user:\n                fragments.append(user)\n        return self.collection_service.merge_ownership(fragments)\n'''
if old_collection not in source:
    raise SystemExit("_get_user_collection marker not found")
source = source.replace(old_collection, new_collection, 1)

legacy_path.write_text(source, encoding="utf-8")
print("patched legacy_main.py")
