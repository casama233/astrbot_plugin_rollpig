from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str, label: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


replace_once(
    "updater.py",
    "import hashlib\n",
    "import hashlib\nimport hmac\n",
    "hmac import",
)
replace_once(
    "updater.py",
    "hashlib.compare_digest(\n",
    "hmac.compare_digest(\n",
    "digest comparison",
)
replace_once(
    "updater.py",
    '"AstrBot-RollPig-Safe-Updater/2.8.0"',
    '"AstrBot-RollPig-Safe-Updater/2.9.1"',
    "updater user agent",
)
replace_once(
    "main.py",
    '"AstrBot-RollPig/2.9.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    '"AstrBot-RollPig/2.9.1 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    "plugin user agent",
)
replace_once(
    "metadata.yaml",
    'version: "2.9.0"',
    'version: "2.9.1"',
    "metadata version",
)
replace_once(
    "CHANGELOG.md",
    "# 更新\n",
    "# 更新\n## v2.9.1 (2026-08-04)\n### 安全更新热修复\n- 修复 SHA-256 校验误调用不存在的 `hashlib.compare_digest`，改用标准库 `hmac.compare_digest`；带 `SHA256SUMS` 的稳定版更新不再报属性错误。\n- 新增回归测试，防止更新器再次引用错误模块。\n\n",
    "changelog header",
)

for relative in (
    ".github/scripts/fix_updater_v291.py",
    ".github/workflows/fix-updater-v291.yml",
):
    (ROOT / relative).unlink(missing_ok=True)
