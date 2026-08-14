from __future__ import annotations

import asyncio

from astrbot.api import logger

try:
    from .renderers import render_pigsty
    from .services.delivery import is_uncertain_send_timeout
except ImportError:  # pragma: no cover - direct module loading compatibility
    from renderers import render_pigsty
    from services.delivery import is_uncertain_send_timeout


class PermanentCollectionMixin:
    """Keep permanent ownership visible when the active resource pool changes.

    ``self.pig_list`` remains the active draw/search catalog. This mixin only
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
        return (
            {str(item) for item in raw if str(item)}
            if isinstance(raw, list)
            else set()
        )

    def _collection_snapshots(self) -> dict:
        history = getattr(self, "history", {})
        snapshots = (
            history.get("pig_snapshots", {}) if isinstance(history, dict) else {}
        )
        return snapshots if isinstance(snapshots, dict) else {}

    def _retired_collection_image_path(self, pig_id: str) -> str:
        """Probe known local roots without emitting missing-image warnings."""
        roots = (
            getattr(self, "custom_image_dir", None),
            getattr(self, "resource_active_dir", None) / "images"
            if getattr(self, "resource_active_dir", None) is not None
            else None,
            getattr(self, "image_dir", None),
        )
        for root in roots:
            if root is None:
                continue
            for ext in getattr(self, "IMAGE_EXTENSIONS", ("png",)):
                path = root / f"{pig_id}.{ext}"
                if path.is_file():
                    return str(path)
        return ""

    def _collection_display_catalog(self, unlocked: dict) -> list[dict]:
        catalog = self.catalog_service.collection_display_catalog(
            self.pig_list,
            unlocked,
            self._collection_snapshots(),
            hidden_ids=self._collection_hidden_ids(),
        )
        for pig in catalog:
            if not pig.get("_collection_retired"):
                continue
            image_path = self._retired_collection_image_path(str(pig.get("id") or ""))
            if image_path:
                pig["_collection_image_path"] = image_path
        return catalog

    def _pigsty_display_state(self, user_id: str) -> tuple[dict, dict, list[dict]]:
        user = self._get_user_collection(user_id)
        if not isinstance(user, dict):
            user = {}
        unlocked = user.get("pigs", {})
        if not isinstance(unlocked, dict):
            unlocked = {}
        return user, unlocked, self._collection_display_catalog(unlocked)

    @staticmethod
    def _active_unlock_count(catalog: list[dict], unlocked: dict) -> int:
        active_ids = {
            str(pig.get("id") or "")
            for pig in catalog
            if isinstance(pig, dict) and str(pig.get("id") or "")
        }
        return len({str(item) for item in unlocked if str(item)}.intersection(active_ids))

    async def my_pigsty(self, event, args: str = ""):
        """Render and deliver the permanent Pigsty without conflating send failures."""
        self._claim_command_event(event)
        page = 1
        raw = str(args or "").strip()
        if raw:
            try:
                page = int(raw.split()[0])
            except ValueError:
                await event.send(event.plain_result("页码格式不正确，例如：/我的猪圈 2"))
                return

        user_id = self._event_sender_id(event)
        user, unlocked, display_catalog = self._pigsty_display_state(user_id)
        total_pages = self.catalog_service.page_count(display_catalog)
        if page < 1 or page > total_pages:
            await event.send(event.plain_result(f"页码范围为 1-{total_pages}。"))
            return

        output = None
        try:
            try:
                output, _ = await asyncio.to_thread(
                    self.render_pigsty_image, user_id, page
                )
            except Exception as exc:
                logger.error(f"生成我的猪圈失败：{exc}", exc_info=True)
                unlocked_count = self._active_unlock_count(self.pig_list, unlocked)
                await event.send(
                    event.plain_result(
                        f"【我的猪圈】已解锁 {unlocked_count}/{len(self.pig_list)}，"
                        "图鉴图片生成失败，请查看后台日志。"
                    )
                )
                return

            try:
                await event.send(event.image_result(str(output.absolute())))
            except Exception as exc:
                if is_uncertain_send_timeout(exc):
                    logger.warning(
                        "发送我的猪圈图片等待 QQ/NTQQ 回执超时；消息可能已成功投递，"
                        "为避免重复图片不重试也不发送失败提示：%s",
                        exc,
                    )
                    return

                logger.error(f"发送我的猪圈图片失败：{exc}", exc_info=True)
                unlocked_count = self._active_unlock_count(self.pig_list, unlocked)
                try:
                    await event.send(
                        event.plain_result(
                            f"【我的猪圈】已解锁 {unlocked_count}/{len(self.pig_list)}，"
                            "图鉴已生成，但图片发送失败，请稍后重试。"
                        )
                    )
                except Exception as fallback_exc:
                    logger.error(
                        f"发送我的猪圈失败提示也失败：{fallback_exc}",
                        exc_info=True,
                    )
        finally:
            if output:
                output.unlink(missing_ok=True)

    def render_pigsty_image(self, user_id: str, page: int):
        """Render active pigs plus this user's retained historical collection."""
        user, unlocked, display_catalog = self._pigsty_display_state(user_id)
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
