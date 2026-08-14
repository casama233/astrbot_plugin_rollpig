from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path): return (ROOT / path).read_text(encoding='utf-8')
def write(path, text): (ROOT / path).write_text(text, encoding='utf-8')
def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {count}')
    return text.replace(old, new, 1)

# Report aggregation: distinguish no-trend ties and incomplete historical detail.
p='daily_report_core.py'; s=read(p)
s=replace_once(s,
'''    popular = top_tied(pig_counts)\n    popular_items = [\n        {"id": pig_id, "name": pig_names.get(pig_id, pig_id), "count": popular["value"]}\n        for pig_id in popular["winners"]\n    ]\n''',
'''    popular = top_tied(pig_counts)\n    popular_has_trend = int(popular["value"] or 0) > 1\n    popular_items = (\n        [\n            {"id": pig_id, "name": pig_names.get(pig_id, pig_id), "count": popular["value"]}\n            for pig_id in popular["winners"]\n        ]\n        if popular_has_trend\n        else []\n    )\n''','popular trend threshold')
s=replace_once(s,
'''    total_roasts = event_roasts if roast_total is None else max(event_roasts, int(roast_total))\n\n    return {\n''',
'''    total_roasts = event_roasts if roast_total is None else max(event_roasts, int(roast_total))\n    roast_detail_missing = max(0, total_roasts - event_roasts)\n\n    return {\n''','roast detail gap')
s=replace_once(s,
'''        "popular_pigs": popular_items,\n        "awards": {\n''',
'''        "popular_pigs": popular_items,\n        "pig_variety": len(pig_counts),\n        "popular_peak": int(popular["value"] or 0),\n        "popular_has_trend": popular_has_trend,\n        "roast_detail_missing": roast_detail_missing,\n        "roast_detail_complete": roast_detail_missing == 0,\n        "awards": {\n''','report transparency fields')
write(p,s)

# Renderer copy: no fake winner when every pig appears once; disclose old aggregate-only roasts.
p='daily_report_feature.py'; s=read(p)
s=replace_once(s,
'''        else:\n            draw.text(\n                (76, pop_y + 105),\n                "今天还没有形成流行趋势。",\n                font=label_font,\n                fill=palette["muted"],\n            )\n\n        awards_y = 846\n''',
'''        else:\n            variety = int(report.get("pig_variety", 0) or 0)\n            peak = int(report.get("popular_peak", 0) or 0)\n            summary = (\n                f"今天 {variety} 种小猪各出现 1 次，尚未形成热门形态。"\n                if variety > 1 and peak == 1\n                else "今天还没有形成流行趋势。"\n            )\n            draw.text(\n                (76, pop_y + 105),\n                summary,\n                font=label_font,\n                fill=palette["muted"],\n            )\n\n        awards_y = 846\n''','no false popular winner')
s=replace_once(s,
'''        draw.text(\n            (68, footer_y + 58),\n            f"自动推送 {self.daily_report_send_time} + 0–{self.daily_report_random_delay_minutes} 分钟随机延迟",\n            font=small_font,\n            fill=palette["secondary"],\n        )\n''',
'''        detail_missing = int(report.get("roast_detail_missing", 0) or 0)\n        footer_line = (\n            f"烤猪总数另含 {detail_missing} 笔仅有总量的历史记录 · 人物称号只按可追溯玩法事件计算"\n            if detail_missing > 0\n            else f"自动推送 {self.daily_report_send_time} + 0–{self.daily_report_random_delay_minutes} 分钟随机延迟"\n        )\n        draw.text(\n            (68, footer_y + 58),\n            footer_line,\n            font=small_font,\n            fill=palette["secondary"],\n        )\n''','report detail disclosure')
write(p,s)

# Cache duplicate index by canonical pig.json mtime; fix Pillow deprecation where possible.
p='source_service/app.py'; s=read(p)
s=replace_once(s,
'''        pixels = list(image.convert("L").resize((9, 8), method).getdata())\n''',
'''        resized = image.convert("L").resize((9, 8), method)\n        getter = getattr(resized, "get_flattened_data", None)\n        pixels = list(getter() if callable(getter) else resized.getdata())\n''','Pillow hash pixels')
s=replace_once(s,
'''        self.admin_token = _read_admin_token(self.config.admin_token_file)\n        self._review_lock = threading.Lock()\n        self._init_database()\n''',
'''        self.admin_token = _read_admin_token(self.config.admin_token_file)\n        self._review_lock = threading.Lock()\n        self._duplicate_index_cache_key: tuple[int, int] | None = None\n        self._duplicate_index_cache: list[dict[str, object]] = []\n        self._init_database()\n''','duplicate cache init')
s=replace_once(s,
'''    def _catalog_duplicate_index(self) -> list[dict[str, object]]:\n        image_root = self.config.catalog_root / "image"\n        index: list[dict[str, object]] = []\n''',
'''    def _catalog_duplicate_index(self) -> list[dict[str, object]]:\n        catalog_path = self.config.catalog_root / "pig.json"\n        try:\n            stat = catalog_path.stat()\n            cache_key = (int(stat.st_mtime_ns), int(stat.st_size))\n        except OSError:\n            cache_key = (-1, -1)\n        if cache_key == self._duplicate_index_cache_key and self._duplicate_index_cache:\n            return [dict(item) for item in self._duplicate_index_cache]\n        image_root = self.config.catalog_root / "image"\n        index: list[dict[str, object]] = []\n''','duplicate cache lookup')
s=replace_once(s,
'''            index.append(item)\n        return index\n\n    def _catalog_ids(self) -> set[str]:\n''',
'''            index.append(item)\n        self._duplicate_index_cache_key = cache_key\n        self._duplicate_index_cache = [dict(item) for item in index]\n        return index\n\n    def _catalog_ids(self) -> set[str]:\n''','duplicate cache store')
write(p,s)

# Commands docs.
p='docs/COMMANDS.md'; s=read(p)
old='''只可在群聊中使用，生成當天卡片化統計海報，包括活躍／抽豬、成功燒烤、被吃、逃脫、反噬、熱門豬，以及「燒烤狂人」「最慘食材」「逃脫大師」「反噬之王」等真實並列稱號。手動查看不觸發可選「今日祭品」。完整自動推送與補發語義見 [`DAILY-REPORT.md`](DAILY-REPORT.md)。\n'''
new='''只可在群聊中使用，生成當天卡片化統計海報，包括活躍／抽豬、成功燒烤、被吃、逃脫、反噬、熱門豬，以及「燒烤狂人」「最慘食材」「逃脫大師」「反噬之王」等真實並列稱號。手動查看不觸發可選「今日祭品」。\n\n自動推送**按群控制且預設關閉**：\n\n- `/豬圈日報 開啟`：群主、群管理員或 AstrBot 管理員開啟本群自動推送；\n- `/豬圈日報 關閉`：關閉本群自動推送，手動查看仍可用；\n- `/豬圈日報 狀態`：查看本群 opt-in 與全局 master switch。\n\n即使全局 `daily_report_auto_send=true`，沒有顯式開啟的群也不會收到推送。完整自動推送與補發語義見 [`DAILY-REPORT.md`](DAILY-REPORT.md)。\n'''
s=replace_once(s,old,new,'daily report command docs')
write(p,s)

# Config docs clarify master switches and current version.
p='docs/CONFIGURATION.md'; s=read(p)
s=s.replace('本文對應 v3.6.3 的 `_conf_schema.json`。','本文對應目前主線的 `_conf_schema.json`。',1)
needle='''## 烤豬與群聊玩法\n'''
insert='''## 豬圈日報\n\n`enable_daily_report` 是整個日報功能的 master switch，`daily_report_auto_send` 是自動推送 master switch；兩者都**不代表所有群自動訂閱**。群組自動推送採 opt-in，既有群與新群預設關閉，需由群主／群管理員／AstrBot 管理員在群內使用 `/豬圈日報 開啟`。`/豬圈日報 狀態` 可查看本群與全局狀態。\n\n'''
if insert not in s:
    s=replace_once(s,needle,insert+needle,'config daily report docs')
write(p,s)

# Tests.
p='tests/test_daily_report.py'; s=read(p)
append='''\n\ndef test_daily_report_does_not_invent_a_popular_pig_for_all_unique_draws():\n    members = [\n        {"user_id": f"u{i}", "pig_id": f"pig-{i}", "pig_name": f"猪{i}"}\n        for i in range(16)\n    ]\n    report = aggregate_daily_report(members, [], [], roast_total=0)\n    assert report["popular_pigs"] == []\n    assert report["pig_variety"] == 16\n    assert report["popular_peak"] == 1\n    assert report["popular_has_trend"] is False\n\n\ndef test_daily_report_discloses_aggregate_only_roast_records():\n    events = [\n        {"kind": "roast_success", "actor_id": "a", "target_id": "b", "victim_id": "b"}\n    ]\n    report = aggregate_daily_report([], events, [], roast_total=3)\n    assert report["roasts"] == 3\n    assert report["roast_detail_missing"] == 2\n    assert report["roast_detail_complete"] is False\n    assert report["awards"]["roast_maniac"] == {"value": 1, "winners": ["a"]}\n'''
if 'test_daily_report_does_not_invent_a_popular_pig_for_all_unique_draws' not in s:
    s += append
write(p,s)

p='tests/test_group_report_source_review_hardening.py'; s=read(p)
append='''\n\ndef test_review_duplicate_index_is_cached_by_catalog_revision():\n    source = (ROOT / "source_service/app.py").read_text(encoding="utf-8")\n    assert "_duplicate_index_cache_key" in source\n    assert "stat.st_mtime_ns" in source\n    assert "get_flattened_data" in source\n'''
if 'test_review_duplicate_index_is_cached_by_catalog_revision' not in s:
    s += append
write(p,s)

print('applied report clarity + duplicate cache')
