from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one marker, got {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# v3.6.3: DailyReportMixin must dispatch through the live instance instead of
# zero-argument super() from a reloaded mixin class. The live instance method
# also records report context, so the explicit second call must be removed.
replace_once(
    "daily_report_feature.py",
    "        actor_id = super()._event_sender_id(event)\n        self._remember_daily_report_context(event, actor_id)\n",
    "        actor_id = self._event_sender_id(event)\n",
)

print("v3.6.3 stability patch applied")
