from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
PAGE = ROOT / "pages" / "pig-manager" / "index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


main = MAIN.read_text(encoding="utf-8")

# Permit browsers that omit Sec-Fetch-Site, while still requiring a matching
# Origin or Referer and rejecting explicitly cross-site requests.
main = replace_once(
    main,
    '''        if not host or sec_fetch_site not in {"same-origin", "same-site"}:
            return False
''',
    '''        if not host or (
            sec_fetch_site and sec_fetch_site not in {"same-origin", "same-site"}
        ):
            return False
''',
    "same-origin browser compatibility",
)

# Avoid attaching arbitrary state to framework request objects. Pass the
# already-parsed body into the CSRF validator instead.
old_csrf = '''    def _request_csrf_token(self) -> str:
        try:
            header = str(request.headers.get("X-RollPig-CSRF", "") or "")
            if header:
                return header
            cached = getattr(request, "_rollpig_payload", None)
            return str(cached.get("__rollpig_csrf", "")) if isinstance(cached, dict) else ""
        except Exception:
            return ""

    def _is_authorized_write_request(self, request_obj) -> bool:
        return self._is_same_origin_request(request_obj) and secrets.compare_digest(
            self._request_csrf_token(), self._csrf_token
        )
'''
new_csrf = '''    def _request_csrf_token(self, request_obj, payload=None) -> str:
        try:
            header = str(request_obj.headers.get("X-RollPig-CSRF", "") or "")
            if header:
                return header
            return (
                str(payload.get("__rollpig_csrf", "") or "")
                if isinstance(payload, dict)
                else ""
            )
        except Exception:
            return ""

    def _is_authorized_write_request(self, request_obj, payload=None) -> bool:
        return self._is_same_origin_request(request_obj) and secrets.compare_digest(
            self._request_csrf_token(request_obj, payload), self._csrf_token
        )
'''
main = replace_once(main, old_csrf, new_csrf, "request-local csrf validation")
main = main.replace(
    '''            setattr(request, "_rollpig_payload", payload if isinstance(payload, dict) else {})
            if not self._is_authorized_write_request(request):
''',
    '''            if not self._is_authorized_write_request(request, payload):
''',
)
if 'setattr(request, "_rollpig_payload"' in main:
    raise RuntimeError("framework request mutation remained after CSRF patch")

# Existing installations keep using their legacy keys so collections and
# penalties are not split. New identities are platform-namespaced.
identity_anchor = '''    def _identity_candidates(self, value: str) -> tuple[str, ...]:
        value = str(value or "").strip()
        legacy = self._legacy_identity(value)
        return (value,) if legacy == value else (value, legacy)

'''
identity_helpers = identity_anchor + '''    def _storage_user_key(self, user_id: str) -> str:
        candidates = self._identity_candidates(str(user_id))
        users = getattr(self, "history", {}).get("users", {})
        for candidate in candidates:
            if candidate in users:
                return candidate
        penalties = getattr(self, "roast_state", {}).get("eaten_penalties", {})
        for candidate in candidates:
            if isinstance(penalties, dict) and candidate in penalties:
                return candidate
        return candidates[0]

    def _storage_group_key(self, group_id: str) -> str:
        candidates = self._identity_candidates(str(group_id))
        daily = getattr(self, "history", {}).get("daily", {})
        for day in daily.values() if isinstance(daily, dict) else ():
            groups = day.get("groups", {}) if isinstance(day, dict) else {}
            for candidate in candidates:
                if isinstance(groups, dict) and candidate in groups:
                    return candidate
        return candidates[0]

'''
main = replace_once(main, identity_anchor, identity_helpers, "legacy storage keys")
main = replace_once(
    main,
    '''        return self._namespace_identity(event, group_id, "group") if group_id else ""
''',
    '''        if not group_id:
            return ""
        return self._storage_group_key(
            self._namespace_identity(event, group_id, "group")
        )
''',
    "legacy group storage",
)

main = replace_once(
    main,
    '''            pig = self._choose_daily_pig(actor_id)
            user_records[actor_id] = pig
            self._record_unlock(
                actor_id,
''',
    '''            storage_id = self._storage_user_key(actor_id)
            pig = self._choose_daily_pig(storage_id)
            user_records[storage_id] = pig
            self._record_unlock(
                storage_id,
''',
    "legacy user storage during draw",
)

# Eaten state and penalties use the same selected legacy/new key across files.
main = replace_once(
    main,
    '''        with self._data_lock:
            records = today_cache.setdefault("records", {})
            previous_pig = records.get(str(user_id))
            records[str(user_id)] = dict(eaten)

            daily = self.history.setdefault("daily", {})
''',
    '''        with self._data_lock:
            storage_id = self._storage_user_key(str(user_id))
            records = today_cache.setdefault("records", {})
            previous_pig = records.get(storage_id)
            records[storage_id] = dict(eaten)

            daily = self.history.setdefault("daily", {})
''',
    "eaten storage key",
)
for old, new in (
    ('daily_records.get(str(user_id))', 'daily_records.get(storage_id)'),
    ('setdefault(str(user_id), original_id)', 'setdefault(storage_id, original_id)'),
    ('daily_records[str(user_id)] = "eaten"', 'daily_records[storage_id] = "eaten"'),
    ('penalties[str(user_id)] = {"due_date": tomorrow, "failed": False}', 'penalties[storage_id] = {"due_date": tomorrow, "failed": False}'),
    ('self._roast_count_key(today, group_id, str(user_id))', 'self._roast_count_key(today, group_id, storage_id)'),
):
    if old not in main:
        raise RuntimeError(f"eaten key replacement missing: {old}")
    main = main.replace(old, new, 1)

old_penalty = '''    def _consume_eaten_penalty(self, user_id: str, today: str) -> bool:
        """在次日首次抽猪时判定吃掉惩罚；失败后锁定到当天结束。"""
        with self._data_lock:
            penalties = self.roast_state.setdefault("eaten_penalties", {})
            if not isinstance(penalties, dict):
                penalties = {}
                self.roast_state["eaten_penalties"] = penalties
            entry = penalties.get(str(user_id))
            if not isinstance(entry, dict):
                return False
            due_date = str(entry.get("due_date") or "")
            if due_date < today:
                penalties.pop(str(user_id), None)
                self._save_roast_state()
                return False
            if due_date != today:
                return False
            if bool(entry.get("failed")):
                return True
            if random.randrange(100) < self.eaten_next_day_failure_percent:
                entry["failed"] = True
                penalties[str(user_id)] = entry
                self._save_roast_state()
                return True
            penalties.pop(str(user_id), None)
            self._save_roast_state()
        return False
'''
new_penalty = '''    def _consume_eaten_penalty(self, user_id: str, today: str) -> bool:
        """在次日首次抽猪时判定吃掉惩罚；失败后锁定到当天结束。"""
        with self._data_lock:
            penalties = self.roast_state.setdefault("eaten_penalties", {})
            if not isinstance(penalties, dict):
                penalties = {}
                self.roast_state["eaten_penalties"] = penalties
            storage_id = self._storage_user_key(str(user_id))
            entry = penalties.get(storage_id)
            if not isinstance(entry, dict):
                return False
            due_date = str(entry.get("due_date") or "")
            if due_date < today:
                penalties.pop(storage_id, None)
                self._save_roast_state()
                return False
            if due_date != today:
                return False
            if bool(entry.get("failed")):
                return True
            if random.randrange(100) < self.eaten_next_day_failure_percent:
                entry["failed"] = True
                penalties[storage_id] = entry
                self._save_roast_state()
                return True
            penalties.pop(storage_id, None)
            self._save_roast_state()
        return False
'''
main = replace_once(main, old_penalty, new_penalty, "legacy penalty lookup")

# Bound text to the fixed canvas. The full text remains in the fallback message.
main = replace_once(
    main,
    '''        if current_line:
            analysis_lines.append(current_line)
        # 计算解析总高度
''',
    '''        if current_line:
            analysis_lines.append(current_line)
        max_analysis_lines = 6
        if len(analysis_lines) > max_analysis_lines:
            analysis_lines = analysis_lines[:max_analysis_lines]
            analysis_lines[-1] = analysis_lines[-1].rstrip("…") + "…"
        # 计算解析总高度
''',
    "main card text bound",
)
main = replace_once(
    main,
    '''        if current:
            lines.append(current)
        for index, line in enumerate(lines):
''',
    '''        if current:
            lines.append(current)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1].rstrip("…") + "…"
        for index, line in enumerate(lines):
''',
    "roast card text bound",
)

ast.parse(main)
MAIN.write_text(main, encoding="utf-8")

page = PAGE.read_text(encoding="utf-8")
page = replace_once(
    page,
    "async function post(path,payload){const body={...(payload||{}),__rollpig_csrf:csrfToken};return unwrap(await bridge.apiPost(path,body,{headers:{'X-RollPig-CSRF':csrfToken}}))}",
    "async function post(path,payload){const body={...(payload||{}),__rollpig_csrf:csrfToken};return unwrap(await bridge.apiPost(path,body))}",
    "bridge-compatible csrf body",
)
page = page.replace(
    "if(canvas)await paintRgbaCanvas(canvas,thumbnail)",
    "if(canvas)await paintRgbaCanvas(canvas,thumbnail)",
)
page = replace_once(
    page,
    "document.querySelectorAll('[data-pig-canvas]').forEach(canvas=>{try{paintRgbaCanvas(canvas,items[+canvas.dataset.pigCanvas].thumbnail)}catch{canvas.closest('.pig-thumb').classList.add('broken')}});",
    "document.querySelectorAll('[data-pig-canvas]').forEach(canvas=>{paintRgbaCanvas(canvas,items[+canvas.dataset.pigCanvas].thumbnail).catch(()=>canvas.closest('.pig-thumb').classList.add('broken'))});",
    "async pig thumbnail errors",
)
page = replace_once(
    page,
    "if(p.thumbnail?.png)paintRgbaCanvas($('imagePreview'),p.thumbnail);",
    "if(p.thumbnail?.png)paintRgbaCanvas($('imagePreview'),p.thumbnail).catch(()=>clearPreview());",
    "async edit preview errors",
)
PAGE.write_text(page, encoding="utf-8")
print("audit fixes postprocessed")
