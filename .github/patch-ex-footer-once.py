from pathlib import Path
import hashlib


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"patch anchor must be unique: {old[:100]!r}")
    return text.replace(old, new, 1)


def read_original(path: str, expected: str) -> str:
    data = Path(path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected:
        raise RuntimeError(f"unexpected baseline for {path}: {actual}")
    return data.decode("utf-8")


static = read_original("renderers/pig_card.py", "8fee53c307423bc5158bbda51ed76fa8ba8aa1fa")
animated = read_original("renderers/animated_pig_card.py", "cd96a585f2ff6505e61e4d1f032245baf1012b7a")
static = replace_once(static, "_PIG_CARD_CACHE_VERSION = 2", "_PIG_CARD_CACHE_VERSION = 3")
static = replace_once(
    static,
    "    spacing_avatar_badge: int = 12\n",
    "    # Retained for constructor compatibility; EX now occupies a footer.\n    spacing_avatar_badge: int = 12\n",
)
static = replace_once(
    static,
    "    ex_badge_padding_y: int = 7\n",
    "    ex_badge_padding_y: int = 7\n    spacing_analysis_badge: int = 24\n    ex_badge_bottom_margin: int = 48\n    content_top_margin: int = 32\n",
)
helper = '''def pig_card_vertical_layout(
    content_height: int,
    badge_height: int,
    layout: PigCardLayout,
) -> tuple[int, int, int | None]:
    """Return canvas height, body top and bottom-anchored EX badge top.

    Short cards keep their original centered artwork/name/copy composition.
    A footer never splits artwork from the name. For longer copy, shift the
    body upward and only grow the canvas when needed to avoid clipping it.
    Static cards and every animated frame share this geometry.
    """
    canvas_height = layout.canvas_height
    if badge_height <= 0:
        return canvas_height, (canvas_height - content_height) // 2, None

    top_margin = max(0, layout.content_top_margin)
    bottom_margin = max(1, layout.ex_badge_bottom_margin)
    gap = max(0, layout.spacing_analysis_badge)
    canvas_height = max(
        canvas_height,
        top_margin + content_height + gap + badge_height + bottom_margin,
    )
    badge_y = canvas_height - bottom_margin - badge_height
    body_y = max(
        top_margin,
        min(
            (canvas_height - content_height) // 2,
            badge_y - gap - content_height,
        ),
    )
    return canvas_height, body_y, badge_y


'''
static = replace_once(static, "def ex_level_badge_metrics(\n", helper + "def ex_level_badge_metrics(\n")
animated = replace_once(
    animated,
    "    ex_level_badge_metrics,\n",
    "    ex_level_badge_metrics,\n    pig_card_vertical_layout,\n",
)

for kind, source in (("static", static), ("animated", animated)):
    source = replace_once(
        source,
        '    canvas_height = layout.canvas_height\n    canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])\n    draw = ImageDraw.Draw(canvas)\n',
        "",
    )
    condition = "show_ex_badge" if kind == "static" else "ex_level is not None"
    source = replace_once(
        source,
        f"    avatar_name_spacing = layout.spacing_avatar_name\n    if {condition}:\n        avatar_name_spacing = (\n            layout.spacing_avatar_badge + badge_h + layout.spacing_badge_name\n        )\n",
        "",
    )
    source = replace_once(source, "        + avatar_name_spacing\n", "        + layout.spacing_avatar_name\n")
    source = replace_once(
        source,
        "    start_y = (canvas_height - total_content_h) // 2\n",
        '    canvas_height, start_y, badge_y = pig_card_vertical_layout(\n        total_content_h, badge_h, layout\n    )\n    canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])\n    draw = ImageDraw.Draw(canvas)\n',
    )
    old_badge = f'''    if {condition}:
        badge_y = avatar_y + avatar_h + layout.spacing_avatar_badge
        draw_ex_level_badge(
            draw,
            center_x=canvas_width // 2,
            top=badge_y,
            ex_level=ex_level,
            palette=palette,
            font_regular=font_regular,
            layout=layout,
        )
        name_y = badge_y + badge_h + layout.spacing_badge_name
    else:
        name_y = avatar_y + avatar_h + layout.spacing_avatar_name
'''
    source = replace_once(
        source, old_badge,
        "    name_y = avatar_y + avatar_h + layout.spacing_avatar_name\n",
    )
    source = replace_once(
        source,
        "        analysis_y += line_height\n",
        '''        analysis_y += line_height

    if badge_y is not None:
        draw_ex_level_badge(
            draw,
            center_x=canvas_width // 2,
            top=badge_y,
            ex_level=ex_level,
            palette=palette,
            font_regular=font_regular,
            layout=layout,
        )
''',
    )
    Path(f"renderers/{'pig_card' if kind == 'static' else 'animated_pig_card'}.py").write_text(source, encoding="utf-8")

changelog = Path("CHANGELOG.md")
changelog.write_text(replace_once(
    changelog.read_text(encoding="utf-8"),
    "## 未發佈\n",
    "## 未發佈\n\n- 單張小豬卡的 `EX Lv.n` 徽章改為底部置中，不再插在圖片與名稱之間；靜態 PNG 與 GIF 共用底部留白及避讓計算，長文案必要時增加卡高，避免遮擋／裁切；同步升級成品快取版本，保留 EX0、未封頂等級及無收藏元資料不顯示徽章的規則。\n",
), encoding="utf-8")

doc = Path("docs/EX-VARIANTS.md")
anchor = "單張靜態卡與 GIF 卡只有在資料明確帶有 `_ex_level` 時才顯示 `EX Lv.n` 徽章：真正的 EX0 會顯示，沒有擁有狀態的預測卡不會被誤標。"
doc.write_text(replace_once(
    doc.read_text(encoding="utf-8"), anchor,
    anchor + "\n\n徽章固定在卡片底部置中，位於完整文案下方，不再插入圖片與名稱之間。PNG 與 GIF 共用相同位置計算：短文案維持原本主體置中；長文案先避讓底部徽章，必要時增加卡高，保留上下留白而不裁切。這只調整顯示版面，不修改 EX 文案、圖片或收藏等級。",
), encoding="utf-8")
print("Applied guarded EX footer patch to both renderers, changelog and EX documentation.")
