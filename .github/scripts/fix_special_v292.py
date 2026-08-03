from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


main_path = ROOT / "main.py"
main = main_path.read_text(encoding="utf-8")
main = replace_once(
    main,
    '''try:
    from .storage import StorageManager, StorageMigrationError
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from storage import StorageManager, StorageMigrationError
    from updater import PluginUpdateManager, UpdateError
''',
    '''try:
    from .rollpig_core import special_pig_state
    from .storage import StorageManager, StorageMigrationError
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state
    from storage import StorageManager, StorageMigrationError
    from updater import PluginUpdateManager, UpdateError
''',
    "core helper import",
)
main = replace_once(
    main,
    '''    ROAST_HUMAN_IDS = {"human"}
    ROAST_EATEN_IDS = {"eaten"}
    ROAST_COOKED_IDS = {"mc_porkchop", "lard-pig"}
    ROAST_HUMAN_NAMES = {"人类", "人類"}
    ROAST_EATEN_NAMES = {"吃掉了"}
    ROAST_COOKED_NAMES = {"猪油", "豬油", "熟食形态", "熟食形態"}
''',
    "",
    "obsolete special constants",
)
old_reason = '''    def _roast_block_reason(self, pig: dict | None) -> str | None:
        """检查一只当天小猪是否仍可被做成料理。"""
        if not pig:
            return "对方今天还没有抽取小猪。"
        pig_id = str(pig.get("id") or "").strip().lower()
        name = str(pig.get("name") or "").strip()
        if pig_id in self.ROAST_HUMAN_IDS or name in self.ROAST_HUMAN_NAMES:
            return "对方今天是「人类」：猪圈劳动合同不支持把人送上烤架。"
        if pig_id in self.ROAST_EATEN_IDS or name in self.ROAST_EATEN_NAMES:
            return "对方今天是「吃掉了」：盘子都空了，不能继续参与烧烤流程。"
        if pig_id in self.ROAST_COOKED_IDS or name in self.ROAST_COOKED_NAMES:
            return f"对方今天是「{name or pig_id}」：已经属于熟食形态，请勿二次加工。"
        return None
'''
new_reason = '''    def _roast_block_reason(
        self, pig: dict | None, *, subject: str = "target"
    ) -> str | None:
        """返回烧烤限制文案，并区分发动者与目标的叙述视角。"""
        state = special_pig_state(pig)
        if state == "normal":
            return None
        actor = subject == "actor"
        if state == "missing":
            return "你今天还没有抽取小猪。" if actor else "对方今天还没有抽取小猪。"
        name = str((pig or {}).get("name") or (pig or {}).get("id") or "特殊形态").strip()
        if state == "human":
            if actor:
                return "你今天是「人类」：只能围观，不能参与猪圈料理。"
            return "对方今天是「人类」：猪圈劳动合同不支持把人送上烤架。"
        if state == "eaten":
            if actor:
                return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
            return "对方今天是「吃掉了」：盘子都空了，不能继续参与烧烤流程。"
        if actor:
            return f"你今天是「{name}」：已经上桌了，不能再次参与烧烤。"
        return f"对方今天是「{name}」：已经是熟食，不能再上一次烤架。"

    def _eat_actor_block_reason(self, pig: dict | None) -> str | None:
        """检查发动者能否使用吃群友，文案始终以“你”指代发动者。"""
        state = special_pig_state(pig)
        if state == "normal":
            return None
        if state == "missing":
            return "你今天还没有抽取小猪，不能发动吃群友。"
        name = str((pig or {}).get("name") or (pig or {}).get("id") or "特殊形态").strip()
        if state == "human":
            return "你今天是「人类」：猪圈菜单不允许人类发动吃群友。"
        if state == "eaten":
            return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
        return f"你今天是「{name}」：已经上桌了，暂时不能去吃群友。"

    def _eat_target_block_reason(self, pig: dict | None) -> str | None:
        """检查目标能否被吃；猪排、猪油等熟食可以直接食用。"""
        state = special_pig_state(pig)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return "对方今天还没有抽取小猪。"
        if state == "human":
            return "对方今天是「人类」：吃人不在猪圈菜单里。"
        return "对方今天已经是「吃掉了」：盘子空了，不能再吃一次。"

    def _eat_success_message(self, pig: dict) -> str:
        """生成与目标形态一致的吃群友成功文案。"""
        name = str(pig.get("name") or pig.get("id") or "今日小猪").strip()
        action = "开袋即食成功" if special_pig_state(pig) == "cooked" else "吃群友成功"
        return f" 🍴 {action}，「{name}」被吃掉了；明天抽猪可能失败。"
'''
main = replace_once(main, old_reason, new_reason, "role-specific special rules")
main = replace_once(
    main,
    '''        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, self._today())
            actor_reason = self._roast_block_reason(actor_pig)
''',
    '''        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, self._today())
            actor_reason = self._roast_block_reason(actor_pig, subject="actor")
''',
    "backlash actor perspective",
)
main = replace_once(
    main,
    '''        actor_pig = self._get_daily_pig(actor_id, self._today())
        actor_reason = self._roast_block_reason(actor_pig)
        if actor_reason:
            await event.send(
                event.plain_result(
                    "你得先有一只可行动的今日小猪。" if not actor_pig else actor_reason
                )
            )
            return
        target_pig = self._get_daily_pig(target_id, self._today())
        target_reason = self._roast_block_reason(target_pig)
''',
    '''        actor_pig = self._get_daily_pig(actor_id, self._today())
        actor_reason = self._eat_actor_block_reason(actor_pig)
        if actor_reason:
            await event.send(event.plain_result(actor_reason))
            return
        target_pig = self._get_daily_pig(target_id, self._today())
        target_reason = self._eat_target_block_reason(target_pig)
''',
    "eat actor and target checks",
)
main = replace_once(
    main,
    '''                " 🍴 被吃群友成功命中，今天变成「吃掉了」；明天抽猪可能失败。",
''',
    '''                self._eat_success_message(target_pig),
''',
    "eat success copy",
)
main = replace_once(
    main,
    '''        user_id = self._event_sender_id(event)
        pig = self._get_daily_pig(user_id, self._today())
        reason = self._roast_block_reason(pig)
''',
    '''        user_id = self._event_sender_id(event)
        pig = self._get_daily_pig(user_id, self._today())
        reason = self._roast_block_reason(pig, subject="actor")
''',
    "self roast perspective",
)
main = replace_once(
    main,
    '''        actor_id = self._event_sender_id(event)
        actor_pig = self._get_daily_pig(actor_id, self._today())
        if self._roast_block_reason(actor_pig):
            await event.send(event.plain_result("你得先有一只可行动的今日小猪。"))
            return
        day = self.history.get("daily", {}).get(self._today().isoformat(), {})
''',
    '''        actor_id = self._event_sender_id(event)
        actor_pig = self._get_daily_pig(actor_id, self._today())
        actor_reason = self._eat_actor_block_reason(actor_pig)
        if actor_reason:
            await event.send(event.plain_result(actor_reason))
            return
        day = self.history.get("daily", {}).get(self._today().isoformat(), {})
''',
    "random eat actor check",
)
main = replace_once(
    main,
    '''            if not self._roast_block_reason(pig) and not protected:
                candidates.append(user_id)
''',
    '''            if not self._eat_target_block_reason(pig) and not protected:
                candidates.append(user_id)
''',
    "random eat target check",
)
main = replace_once(
    main,
    '''                event.plain_result("今天本群没有可吃的群友：可能都已被吃、是特殊形态或受保护。")
''',
    '''                event.plain_result("今天本群没有可吃的群友：可能尚未抽取、已经被吃、是人类或受保护。")
''',
    "random eat empty copy",
)
main = main.replace("AstrBot-RollPig/2.9.1", "AstrBot-RollPig/2.9.2")
main_path.write_text(main, encoding="utf-8", newline="\n")

core_path = ROOT / "rollpig_core.py"
core = core_path.read_text(encoding="utf-8")
core += '''

_SPECIAL_HUMAN_IDS = frozenset({"human"})
_SPECIAL_EATEN_IDS = frozenset({"eaten"})
_SPECIAL_COOKED_IDS = frozenset({"mc_porkchop", "lard-pig"})
_SPECIAL_HUMAN_NAMES = frozenset({"人类", "人類"})
_SPECIAL_EATEN_NAMES = frozenset({"吃掉了"})
_SPECIAL_COOKED_NAMES = frozenset({"猪油", "豬油", "熟食形态", "熟食形態"})


def special_pig_state(pig: dict | None) -> str:
    """Classify only the special states that alter cooking/eating eligibility."""
    if not isinstance(pig, dict) or not pig:
        return "missing"
    pig_id = str(pig.get("id") or "").strip().lower()
    name = str(pig.get("name") or "").strip()
    if pig_id in _SPECIAL_HUMAN_IDS or name in _SPECIAL_HUMAN_NAMES:
        return "human"
    if pig_id in _SPECIAL_EATEN_IDS or name in _SPECIAL_EATEN_NAMES:
        return "eaten"
    if pig_id in _SPECIAL_COOKED_IDS or name in _SPECIAL_COOKED_NAMES:
        return "cooked"
    return "normal"
'''
core_path.write_text(core, encoding="utf-8", newline="\n")

updater_path = ROOT / "updater.py"
updater = updater_path.read_text(encoding="utf-8").replace(
    "AstrBot-RollPig-Safe-Updater/2.9.1",
    "AstrBot-RollPig-Safe-Updater/2.9.2",
)
updater_path.write_text(updater, encoding="utf-8", newline="\n")

metadata_path = ROOT / "metadata.yaml"
metadata = metadata_path.read_text(encoding="utf-8")
metadata = replace_once(metadata, 'version: "2.9.1"', 'version: "2.9.2"', "metadata version")
metadata_path.write_text(metadata, encoding="utf-8", newline="\n")

changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
section = '''# 更新
## v2.9.2 (2026-08-04)
### 特殊形态判定与文案
- 修复 `/吃群友` 检查发动者时沿用目标视角，导致发动者抽到猪排却错误提示“对方今天是猪排”的问题。
- 分离发动者、烧烤目标与进食目标的资格规则：人类和“吃掉了”仍不可参与；猪排、猪油等熟食不能主动行动或重复烧烤，但现在可以被正常吃掉。
- 机械猪等普通特殊猪不会被误判为熟食；吃群友成功文案会显示实际目标名称，熟食目标使用“开袋即食”文案。

'''
changelog = replace_once(changelog, "# 更新\n", section, "changelog heading")
changelog_path.write_text(changelog, encoding="utf-8", newline="\n")

core_tests_path = ROOT / "tests" / "test_rollpig_core.py"
core_tests = core_tests_path.read_text(encoding="utf-8")
core_tests = replace_once(
    core_tests,
    '''    pre_instance_identity,
)
''',
    '''    pre_instance_identity,
    special_pig_state,
)
''',
    "core test import",
)
core_tests += '''


def test_special_pig_state_keeps_cooking_roles_distinct():
    assert special_pig_state(None) == "missing"
    assert special_pig_state({"id": "human", "name": "人类"}) == "human"
    assert special_pig_state({"id": "eaten", "name": "吃掉了"}) == "eaten"
    assert special_pig_state({"id": "mc_porkchop", "name": "猪排"}) == "cooked"
    assert special_pig_state({"id": "lard-pig", "name": "猪油"}) == "cooked"
    assert special_pig_state({"id": "mechanical-pig", "name": "机械猪"}) == "normal"
'''
core_tests_path.write_text(core_tests, encoding="utf-8", newline="\n")

source_tests_path = ROOT / "tests" / "test_source_regressions.py"
source_tests = source_tests_path.read_text(encoding="utf-8")
source_tests += '''


def test_special_pig_copy_separates_actor_roast_and_eat_targets():
    eat = ast.get_source_segment(SOURCE, _method("_eat_group_target")) or ""
    random_eat = ast.get_source_segment(SOURCE, _method("eat_random_group_member")) or ""
    self_roast = ast.get_source_segment(SOURCE, _method("roast_today_pig")) or ""
    actor_rules = ast.get_source_segment(SOURCE, _method("_eat_actor_block_reason")) or ""
    target_rules = ast.get_source_segment(SOURCE, _method("_eat_target_block_reason")) or ""
    success_copy = ast.get_source_segment(SOURCE, _method("_eat_success_message")) or ""

    assert "_eat_actor_block_reason(actor_pig)" in eat
    assert "_eat_target_block_reason(target_pig)" in eat
    assert "_eat_actor_block_reason(actor_pig)" in random_eat
    assert "_eat_target_block_reason(pig)" in random_eat
    assert '_roast_block_reason(pig, subject="actor")' in self_roast
    assert "你今天是" in actor_rules
    assert 'state in {"normal", "cooked"}' in target_rules
    assert "开袋即食成功" in success_copy
'''
source_tests_path.write_text(source_tests, encoding="utf-8", newline="\n")
