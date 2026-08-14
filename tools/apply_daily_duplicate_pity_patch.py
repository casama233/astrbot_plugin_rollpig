from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}: found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Wire new configuration into the plugin without changing persistence semantics.
main_path = ROOT / "main.py"
replace_once(
    main_path,
    '''        self.pity_step_percent = min(50, max(0, pity_step))\n        self.enable_roast: bool = self.config.get("enable_roast", True)\n''',
    '''        self.pity_step_percent = min(50, max(0, pity_step))\n        self.enable_daily_duplicate_pity: bool = self.config.get(\n            "enable_daily_duplicate_pity", True\n        )\n        try:\n            daily_pity_start_day = int(\n                self.config.get("daily_duplicate_pity_start_day", 2)\n            )\n        except (TypeError, ValueError):\n            daily_pity_start_day = 2\n        self.daily_duplicate_pity_start_day = min(7, max(2, daily_pity_start_day))\n        try:\n            daily_pity_step = int(\n                self.config.get("daily_duplicate_pity_step_percent", 5)\n            )\n        except (TypeError, ValueError):\n            daily_pity_step = 5\n        self.daily_duplicate_pity_step_percent = min(25, max(0, daily_pity_step))\n        try:\n            daily_pity_max = int(\n                self.config.get("daily_duplicate_pity_max_percent", 15)\n            )\n        except (TypeError, ValueError):\n            daily_pity_max = 15\n        self.daily_duplicate_pity_max_percent = min(50, max(0, daily_pity_max))\n        self.enable_roast: bool = self.config.get("enable_roast", True)\n''',
)
replace_once(
    main_path,
    '''        self.draw_service = DrawService(\n            enable_new_pig_pity=self.enable_new_pig_pity,\n            pity_step_percent=self.pity_step_percent,\n        )\n''',
    '''        self.draw_service = DrawService(\n            enable_new_pig_pity=self.enable_new_pig_pity,\n            pity_step_percent=self.pity_step_percent,\n            enable_daily_duplicate_pity=self.enable_daily_duplicate_pity,\n            daily_duplicate_pity_start_day=self.daily_duplicate_pity_start_day,\n            daily_duplicate_pity_step_percent=self.daily_duplicate_pity_step_percent,\n            daily_duplicate_pity_max_percent=self.daily_duplicate_pity_max_percent,\n        )\n''',
)


# 2. Replace the pure selection service with an explicitly testable probability policy.
draw_service = '''from __future__ import annotations\n\nimport random\nfrom dataclasses import dataclass\nfrom typing import Any, Mapping, Sequence\n\n\n@dataclass(frozen=True)\nclass DrawService:\n    """Pure daily-draw selection policy, independent from persistence and AstrBot."""\n\n    enable_new_pig_pity: bool = True\n    pity_step_percent: int = 15\n    enable_daily_duplicate_pity: bool = True\n    daily_duplicate_pity_start_day: int = 2\n    daily_duplicate_pity_step_percent: int = 5\n    daily_duplicate_pity_max_percent: int = 15\n    max_pity_percent: int = 80\n\n    @staticmethod\n    def _duplicate_streak(collection: Mapping[str, Any] | None) -> int:\n        user = collection if isinstance(collection, Mapping) else {}\n        try:\n            return max(0, int(user.get("duplicate_streak", 0) or 0))\n        except (TypeError, ValueError):\n            return 0\n\n    def pity_chance(self, collection: Mapping[str, Any] | None) -> float:\n        """Return the reroll-to-unseen probability for a duplicate candidate.\n\n        ``duplicate_streak`` is the persisted count of consecutive completed daily\n        draws that were already unlocked.  Therefore a streak of 1 means the next\n        candidate is the second consecutive duplicate day.\n        """\n        streak = self._duplicate_streak(collection)\n\n        base_percent = 0\n        if self.enable_new_pig_pity:\n            base_percent = streak * max(0, int(self.pity_step_percent))\n\n        daily_bonus_percent = 0\n        if self.enable_daily_duplicate_pity:\n            start_day = min(7, max(2, int(self.daily_duplicate_pity_start_day)))\n            step_percent = max(0, int(self.daily_duplicate_pity_step_percent))\n            bonus_cap = max(0, int(self.daily_duplicate_pity_max_percent))\n            current_duplicate_day = streak + 1\n            if current_duplicate_day >= start_day:\n                bonus_layers = current_duplicate_day - start_day + 1\n                daily_bonus_percent = min(bonus_cap, bonus_layers * step_percent)\n\n        total_percent = min(\n            max(0, int(self.max_pity_percent)),\n            base_percent + daily_bonus_percent,\n        )\n        return total_percent / 100\n\n    def choose(\n        self,\n        pigs: Sequence[Mapping[str, Any]],\n        collection: Mapping[str, Any] | None,\n        *,\n        rng: Any = random,\n    ) -> dict[str, Any]:\n        if not pigs:\n            raise ValueError("pig catalog is empty")\n        chosen = dict(rng.choice(pigs))\n        if not (self.enable_new_pig_pity or self.enable_daily_duplicate_pity):\n            return chosen\n\n        user = collection if isinstance(collection, Mapping) else {}\n        unlocked_raw = user.get("pigs")\n        unlocked = set(unlocked_raw) if isinstance(unlocked_raw, Mapping) else set()\n        unseen = [pig for pig in pigs if str(pig.get("id") or "") not in unlocked]\n        chosen_id = str(chosen.get("id") or "")\n        if not unseen or chosen_id not in unlocked:\n            return chosen\n\n        chance = self.pity_chance(user)\n        return dict(rng.choice(unseen)) if rng.random() < chance else chosen\n'''
(ROOT / "services" / "draw_service.py").write_text(draw_service, encoding="utf-8")


# 3. Add administrator-facing config keys next to the existing pity settings.
schema_path = ROOT / "_conf_schema.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
new_schema: dict[str, object] = {}
for key, value in schema.items():
    new_schema[key] = value
    if key == "pity_step_percent":
        new_schema["enable_daily_duplicate_pity"] = {
            "description": "开启跨日重复疲劳保底",
            "hint": "连续多个自然日抽到已解锁小猪时，从指定天数开始额外提高重抽新猪概率；与原连续重复保底叠加但共同受 80% 总上限限制",
            "type": "bool",
            "default": True,
        }
        new_schema["daily_duplicate_pity_start_day"] = {
            "description": "跨日疲劳保底起算日",
            "hint": "连续重复到第几天开始获得额外加成，范围 2-7，默认第 2 天",
            "type": "int",
            "default": 2,
        }
        new_schema["daily_duplicate_pity_step_percent"] = {
            "description": "跨日疲劳每层增加概率（百分比）",
            "hint": "从起算日开始，每多连续重复一天增加的额外概率，范围 0-25，默认 5",
            "type": "int",
            "default": 5,
        }
        new_schema["daily_duplicate_pity_max_percent"] = {
            "description": "跨日疲劳额外加成上限（百分比）",
            "hint": "跨日疲劳机制最多额外增加多少概率，范围 0-50，默认 15；最终保底概率仍封顶 80%",
            "type": "int",
            "default": 15,
        }
schema_path.write_text(
    json.dumps(new_schema, ensure_ascii=False, indent=4) + "\n",
    encoding="utf-8",
)


# 4. Document the behavior and defaults.
config_doc = ROOT / "docs" / "CONFIGURATION.md"
replace_once(
    config_doc,
    '''| `pity_step_percent` | int | `15` | `0-50` | 每連續重複一次，下一次重抽未解鎖小豬的概率增量百分點。設為 `0` 等同保留機制但不增加概率。 |\n| `timezone` | string | `local` | IANA 時區或 `local` | 每日邊界時區，例如 `Asia/Hong_Kong`、`Asia/Shanghai`、`America/Los_Angeles`。`local` 使用伺服器系統時區。 |\n''',
    '''| `pity_step_percent` | int | `15` | `0-50` | 原連續重複保底：每個既有的連續重複日，下一次重抽未解鎖小豬的概率增加多少百分點。 |\n| `enable_daily_duplicate_pity` | bool | `true` | `true` / `false` | 啟用跨自然日的「重複疲勞」額外加成；可獨立於原保底開關。 |\n| `daily_duplicate_pity_start_day` | int | `2` | `2-7` | 連續第幾個重複日開始追加跨日疲勞加成。 |\n| `daily_duplicate_pity_step_percent` | int | `5` | `0-25` | 從起算日開始，每增加一個連續重複日追加的概率百分點。 |\n| `daily_duplicate_pity_max_percent` | int | `15` | `0-50` | 跨日疲勞額外加成的獨立上限；原保底與此加成相加後仍共同封頂 `80%`。 |\n| `timezone` | string | `local` | IANA 時區或 `local` | 每日邊界時區，例如 `Asia/Hong_Kong`、`Asia/Shanghai`、`America/Los_Angeles`。`local` 使用伺服器系統時區。 |\n\n### 跨日重複疲勞保底如何計算\n\n`duplicate_streak` 只會在真正完成一個新的每日抽取後更新，因此同一天反覆查看 `/今日小豬` 不會堆疊跨日層數。抽到未解鎖小豬時，連續重複會立即歸零。\n\n預設值下，若下一次候選仍是已解鎖小豬：第 2 個連續重複日的額外跨日加成為 `+5%`，第 3 日為 `+10%`，第 4 日起封頂 `+15%`。它會與原 `duplicate_streak × pity_step_percent` 相加，但最終重抽未解鎖小豬的概率仍不超過 `80%`。\n''',
)
replace_once(
    config_doc,
    '''  "enable_new_pig_pity": true,\n  "pity_step_percent": 15,\n  "enable_roast": true,\n''',
    '''  "enable_new_pig_pity": true,\n  "pity_step_percent": 15,\n  "enable_daily_duplicate_pity": true,\n  "daily_duplicate_pity_start_day": 2,\n  "daily_duplicate_pity_step_percent": 5,\n  "daily_duplicate_pity_max_percent": 15,\n  "enable_roast": true,\n''',
)

readme = ROOT / "README.md"
replace_once(
    readme,
    "- **重複保底**：可配置提高下一次抽到未解鎖小豬的機率。\n",
    "- **重複保底**：原連續重複保底之外，可配置跨自然日的重複疲勞加成；抽中新豬即重置，總保底率仍封頂 80%。\n",
)


# 5. Add focused unit coverage for legacy compatibility and the new daily layer.
test_path = ROOT / "tests" / "test_draw_service_pity.py"
test_path.write_text(
    '''from __future__ import annotations\n\nimport pytest\n\nfrom services.draw_service import DrawService\n\n\nclass StubRng:\n    def __init__(self, first_choice, random_value: float):\n        self.first_choice = first_choice\n        self.random_value = random_value\n        self.choice_calls = 0\n\n    def choice(self, items):\n        self.choice_calls += 1\n        if self.choice_calls == 1:\n            return self.first_choice\n        return items[0]\n\n    def random(self):\n        return self.random_value\n\n\ndef test_legacy_pity_is_unchanged_when_daily_bonus_is_disabled():\n    service = DrawService(\n        enable_new_pig_pity=True,\n        pity_step_percent=15,\n        enable_daily_duplicate_pity=False,\n    )\n    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)\n    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.15)\n    assert service.pity_chance({"duplicate_streak": 2}) == pytest.approx(0.30)\n\n\ndef test_daily_bonus_starts_on_second_consecutive_duplicate_day():\n    service = DrawService()\n    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)\n    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.20)\n    assert service.pity_chance({"duplicate_streak": 2}) == pytest.approx(0.40)\n    assert service.pity_chance({"duplicate_streak": 3}) == pytest.approx(0.60)\n    assert service.pity_chance({"duplicate_streak": 4}) == pytest.approx(0.75)\n\n\ndef test_daily_bonus_has_independent_switch_and_can_work_without_legacy_pity():\n    service = DrawService(\n        enable_new_pig_pity=False,\n        enable_daily_duplicate_pity=True,\n        daily_duplicate_pity_start_day=2,\n        daily_duplicate_pity_step_percent=5,\n        daily_duplicate_pity_max_percent=15,\n    )\n    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)\n    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.05)\n    assert service.pity_chance({"duplicate_streak": 3}) == pytest.approx(0.15)\n    assert service.pity_chance({"duplicate_streak": 20}) == pytest.approx(0.15)\n\n\ndef test_combined_pity_never_exceeds_eighty_percent():\n    service = DrawService()\n    assert service.pity_chance({"duplicate_streak": 20}) == pytest.approx(0.80)\n\n\ndef test_choose_rerolls_duplicate_to_unseen_when_combined_pity_hits():\n    duplicate = {"id": "owned", "name": "Owned"}\n    unseen = {"id": "new", "name": "New"}\n    service = DrawService()\n    rng = StubRng(duplicate, random_value=0.19)\n\n    chosen = service.choose(\n        [duplicate, unseen],\n        {"pigs": {"owned": {"count": 1}}, "duplicate_streak": 1},\n        rng=rng,\n    )\n\n    assert chosen["id"] == "new"\n\n\ndef test_choose_keeps_duplicate_when_roll_misses_combined_pity():\n    duplicate = {"id": "owned", "name": "Owned"}\n    unseen = {"id": "new", "name": "New"}\n    service = DrawService()\n    rng = StubRng(duplicate, random_value=0.20)\n\n    chosen = service.choose(\n        [duplicate, unseen],\n        {"pigs": {"owned": {"count": 1}}, "duplicate_streak": 1},\n        rng=rng,\n    )\n\n    assert chosen["id"] == "owned"\n''',
    encoding="utf-8",
)
