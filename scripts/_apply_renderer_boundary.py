from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy_main.py"

REL_IMPORT = """    from .renderers import (\n        PigCardLayout,\n        WeeklyEntry,\n        draw_bold_text as renderer_draw_bold_text,\n        fit_card_image as renderer_fit_card_image,\n        get_text_size as renderer_get_text_size,\n        render_catalog_grid as render_catalog_grid_image,\n        render_pig_card,\n        render_pigsty,\n        render_weekly_summary as render_weekly_summary_image,\n    )\n"""
DIRECT_IMPORT = """    from renderers import (\n        PigCardLayout,\n        WeeklyEntry,\n        draw_bold_text as renderer_draw_bold_text,\n        fit_card_image as renderer_fit_card_image,\n        get_text_size as renderer_get_text_size,\n        render_catalog_grid as render_catalog_grid_image,\n        render_pig_card,\n        render_pigsty,\n        render_weekly_summary as render_weekly_summary_image,\n    )\n"""


def insert_imports(source: str) -> str:
    rel_anchor = (
        "    from .services import CatalogService, DrawService, "
        "ResourceReadService, RoastService\n"
    )
    direct_anchor = (
        "    from services import CatalogService, DrawService, "
        "ResourceReadService, RoastService\n"
    )
    if "render_pig_card" not in source:
        if rel_anchor not in source or direct_anchor not in source:
            raise RuntimeError("renderer import anchor missing")
        source = source.replace(rel_anchor, rel_anchor + REL_IMPORT, 1)
        source = source.replace(direct_anchor, direct_anchor + DIRECT_IMPORT, 1)
    return source


def replace_methods(source: str, replacements: dict[str, str]) -> str:
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    methods = {
        node.name: node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    lines = source.splitlines(keepends=True)
    edits = []
    for name, replacement in replacements.items():
        node = methods.get(name)
        if node is None or node.end_lineno is None:
            raise RuntimeError(f"method not found: {name}")
        edits.append((node.lineno - 1, node.end_lineno, replacement.rstrip() + "\n"))
    for start, end, replacement in sorted(edits, reverse=True):
        lines[start:end] = [replacement]
    return "".join(lines)


REPLACEMENTS = {
    "_get_text_size": '''    def _get_text_size(
        self, text: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int]:
        """Compatibility facade for shared renderer text measurement."""
        return renderer_get_text_size(text, font)
''',
    "_draw_bold_text": '''    def _draw_bold_text(
        self,
        draw: ImageDraw.ImageDraw,
        pos: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: tuple,
    ):
        """Compatibility facade for the shared synthetic-bold primitive."""
        renderer_draw_bold_text(draw, pos, text, font, fill)
''',
    "_fit_card_image": '''    def _fit_card_image(self, path: Path, size: tuple[int, int]) -> PILImage.Image:
        """Compatibility facade for the shared card-image primitive."""
        return renderer_fit_card_image(path, size)
''',
    "render_pig_image": '''    def render_pig_image(self, pig_data: dict) -> Path | None:
        """Prepare plugin-owned dependencies, then delegate single-pig drawing."""
        return render_pig_card(
            pig_data,
            palette=self._image_palette(),
            font_bold=self.font_bold,
            font_regular=self.font_regular,
            image_resolver=self.find_image_file,
            layout=PigCardLayout(
                canvas_width=self.CANVAS_WIDTH,
                canvas_height=self.CANVAS_HEIGHT,
                avatar_size=self.AVATAR_SIZE,
                spacing_avatar_name=self.SPACING_AVATAR_NAME,
                spacing_name_desc=self.SPACING_NAME_DESC,
                spacing_desc_analysis=self.SPACING_DESC_ANALYSIS,
                desc_font_size=self.DESC_FONT_SIZE,
                analysis_font_size=self.ANALYSIS_FONT_SIZE,
                analysis_line_height_factor=self.ANALYSIS_LINE_HEIGHT_FACTOR,
                analysis_width_ratio=self.ANALYSIS_WIDTH_RATIO,
            ),
        )
''',
    "render_pigsty_image": '''    def render_pigsty_image(self, user_id: str, page: int) -> tuple[Path, int]:
        """Prepare collection reads, then delegate permanent-catalog drawing."""
        user = self._get_user_collection(user_id)
        if not isinstance(user, dict):
            user = {}
        unlocked = user.get("pigs", {})
        if not isinstance(unlocked, dict):
            unlocked = {}
        ordered_pigs = self.catalog_service.ordered_for_collection(
            self.pig_list, unlocked
        )
        favorite_id = ""
        favorite_count = 0
        for item_id, record in unlocked.items():
            if not isinstance(record, dict):
                continue
            count = int(record.get("count", 0) or 0)
            if count > favorite_count:
                favorite_id, favorite_count = str(item_id), count
        favorite = (
            self.catalog_service.find(self.pig_list, favorite_id)
            if favorite_id
            else None
        )
        favorite_name = str(favorite.get("name")) if favorite else "暂无"
        return render_pigsty(
            catalog=self.pig_list,
            user=user,
            ordered_pigs=ordered_pigs,
            favorite_name=favorite_name,
            page=page,
            total_pages=self.catalog_service.page_count(self.pig_list),
            page_size=self.CATALOG_PAGE_SIZE,
            palette=self._image_palette(),
            font_bold=self.font_bold,
            font_regular=self.font_regular,
            image_resolver=self.find_image_file,
        )
''',
    "render_catalog_grid": '''    def render_catalog_grid(
        self, pigs: list[dict], title: str, subtitle: str
    ) -> Path:
        """Delegate random/search grid drawing to the renderer boundary."""
        return render_catalog_grid_image(
            pigs,
            title,
            subtitle,
            palette=self._image_palette(),
            font_bold=self.font_bold,
            font_regular=self.font_regular,
            image_resolver=self.find_image_file,
        )
''',
    "render_weekly_summary": '''    def render_weekly_summary(self, user_id: str) -> Path:
        """Prepare weekly domain reads, then delegate drawing."""
        today = self._today()
        monday = today - datetime.timedelta(days=today.weekday())
        entries: list[WeeklyEntry] = []
        for index in range(7):
            day = monday + datetime.timedelta(days=index)
            pig, was_eaten = self._get_weekly_pig(user_id, day)
            entries.append(WeeklyEntry(day=day, pig=pig, was_eaten=was_eaten))
        return render_weekly_summary_image(
            entries,
            today=today,
            monday=monday,
            palette=self._image_palette(),
            font_bold=self.font_bold,
            font_regular=self.font_regular,
            image_resolver=self.find_image_file,
        )
''',
}


source = LEGACY.read_text(encoding="utf-8")
source = insert_imports(source)
source = replace_methods(source, REPLACEMENTS)
LEGACY.write_text(source, encoding="utf-8")

architecture = ROOT / "docs" / "ARCHITECTURE.md"
arch_text = architecture.read_text(encoding="utf-8")
marker = "## Renderer Boundary\n"
if marker not in arch_text:
    arch_text += '''\n\n## Renderer Boundary\n\n第三階段把單豬卡、永久圖鑑、隨機／搜尋九宮格與本週小豬的 PIL 繪製移入 `renderers/`。renderer 不 import AstrBot，不讀寫 storage，不知道資源同步、命令事件或插件生命周期。\n\n`legacy_main.py` 只保留 compatibility facade：先從既有 domain read API 準備 collection／weekly entries、palette 與字體，再把明確輸入交給 renderer。圖片路徑仍經 `find_image_file()` → `ResourceReadService`；圖鑑排序／查找／頁數仍經 `CatalogService`，renderer 不重新實作 precedence 或 catalog policy。\n\n目前 `render_roast_image`、管理面板縮圖與其他舊圖像輸出尚在 `legacy_main.py`。後續應按同一原則逐個拆分，而不是讓 `renderers/` 取得整個 plugin instance。\n'''
    architecture.write_text(arch_text, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
change_text = changelog.read_text(encoding="utf-8")
bullet = "- 完成 renderer boundary 第三階段"
if bullet not in change_text:
    anchor = "- 新增 `ResourceReadService` 固定 local override → EX variant → cloud → bundled 圖片解析順位，並以單元與 AST 契約測試鎖定；PIL renderer、同步、寫入、storage schema 與資源協議均不變。\n"
    addition = (
        "- 完成 renderer boundary 第三階段：單豬卡、永久圖鑑、隨機／搜尋九宮格與本週小豬的 PIL 繪製移入 `renderers/`；`legacy_main.py` 僅準備 domain read model 與視圖依賴後委派。\n"
        "- 新增 renderer 架構契約與獨立輸出 smoke；`renderers/` 禁止 AstrBot/storage/同步依賴，collection 與 weekly domain read 仍留在插件 orchestration，視覺與命令行為不變。\n"
    )
    if anchor not in change_text:
        raise RuntimeError("changelog renderer anchor missing")
    change_text = change_text.replace(anchor, anchor + addition, 1)
    changelog.write_text(change_text, encoding="utf-8")

print("renderer boundary applied")
