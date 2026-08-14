from __future__ import annotations

try:
    from .renderers import render_pigsty
except ImportError:  # pragma: no cover - direct module loading compatibility
    from renderers import render_pigsty


class PermanentCollectionMixin:
    """Keep permanent ownership visible when the active resource pool changes.

    ``self.pig_list`` remains the active draw/search catalog.  This mixin only
    builds a user-specific read model for ``/我的猪圈`` by appending unlocked
    historical snapshots that are no longer present in the active source.
    """

    def _collection_hidden_ids(self) -> set[str]:
        """Respect explicit administrator tombstones in the permanent view."""
        try:
            raw = self._runtime_document(
                "catalog_tombstones", self.tombstones_path, []
            )
        except Exception:
            raw = []
        return {str(item) for item in raw if str(item)} if isinstance(raw, list) else set()

    def _collection_snapshots(self) -> dict:
        history = getattr(self, "history", {})
        snapshots = history.get("pig_snapshots", {}) if isinstance(history, dict) else {}
        return snapshots if isinstance(snapshots, dict) else {}

    def _collection_display_catalog(self, unlocked: dict) -> list[dict]:
        return self.catalog_service.collection_display_catalog(
            self.pig_list,
            unlocked,
            self._collection_snapshots(),
            hidden_ids=self._collection_hidden_ids(),
        )

    def render_pigsty_image(self, user_id: str, page: int):
        """Render active pigs plus this user's retained historical collection."""
        user = self._get_user_collection(user_id)
        if not isinstance(user, dict):
            user = {}
        unlocked = user.get("pigs", {})
        if not isinstance(unlocked, dict):
            unlocked = {}

        display_catalog = self._collection_display_catalog(unlocked)
        favorite_id = ""
        favorite_count = 0
        for item_id, record in unlocked.items():
            if not isinstance(record, dict):
                continue
            try:
                count = int(record.get("count", 0) or 0)
            except (TypeError, ValueError):
                count = 0
            if count > favorite_count:
                favorite_id = str(item_id)
                favorite_count = count

        favorite = (
            self.catalog_service.find(display_catalog, favorite_id)
            if favorite_id
            else None
        )
        favorite_name = str(favorite.get("name")) if favorite else "暂无"

        return render_pigsty(
            catalog=self.pig_list,
            user=user,
            ordered_pigs=display_catalog,
            favorite_name=favorite_name,
            page=page,
            total_pages=self.catalog_service.page_count(display_catalog),
            page_size=self.CATALOG_PAGE_SIZE,
            palette=self._image_palette(),
            font_bold=self.font_bold,
            font_regular=self.font_regular,
            image_resolver=self.find_image_file,
        )
