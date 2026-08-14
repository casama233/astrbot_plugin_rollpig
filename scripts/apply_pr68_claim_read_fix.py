from pathlib import Path

path = Path('legacy_main.py')
text = path.read_text(encoding='utf-8')
old = '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:
        """Return only identity fragments proven to belong to this logical user."""
        candidates = self._identity_candidates(str(user_id))
        if len(candidates) == 1:
            return candidates
        namespaced = candidates[0]
        storage_key = self._storage_user_key(namespaced)
        claims_root = getattr(self, "history", {}).get("identity_claims", {})
        user_claims = (
            claims_root.get("users", {})
            if isinstance(claims_root, dict)
            else {}
        )
        return self.collection_service.claimed_read_candidates(
            candidates,
            user_claims,
            preferred_storage_key=storage_key,
        )
'''
new = '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:
        """Return only identity fragments proven to belong to this logical user.

        Read recovery must not stop merely because the current namespaced key
        already exists: older pre-instance/raw fragments may still contain
        permanent ownership.  Each legacy candidate is considered only from the
        current identity candidate pool and must pass the existing claim policy
        before it may participate in collection reads.
        """
        candidates = self._identity_candidates(str(user_id))
        if len(candidates) == 1:
            return candidates
        namespaced = candidates[0]

        # Preserve the canonical write/storage decision, then independently
        # discover claim-safe legacy fragments for ownership reads.  This avoids
        # the historical short-circuit where an existing namespaced row hid all
        # older ownership fragments.
        storage_key = self._storage_user_key(namespaced)
        users = getattr(self, "history", {}).get("users", {})
        penalties = getattr(self, "roast_state", {}).get("eaten_penalties", {})
        preferred_keys = [storage_key]
        for legacy in candidates[1:]:
            legacy_exists = (
                (isinstance(users, dict) and legacy in users)
                or (isinstance(penalties, dict) and legacy in penalties)
                or self._identity_exists(legacy)
            )
            if not legacy_exists:
                continue
            claimed_key = self._claim_legacy_identity(
                namespaced,
                legacy,
                kind="users",
                legacy_exists=True,
            )
            if claimed_key == legacy and claimed_key not in preferred_keys:
                preferred_keys.append(claimed_key)

        claims_root = getattr(self, "history", {}).get("identity_claims", {})
        user_claims = (
            claims_root.get("users", {})
            if isinstance(claims_root, dict)
            else {}
        )
        return self.collection_service.claimed_read_candidates(
            candidates,
            user_claims,
            preferred_storage_keys=tuple(preferred_keys),
        )
'''
if text.count(old) != 1:
    raise SystemExit(f'expected one _user_read_candidates block, found {text.count(old)}')
path.write_text(text.replace(old, new), encoding='utf-8')

svc = Path('services/collection_service.py')
s = svc.read_text(encoding='utf-8')
s = s.replace('''        preferred_storage_key: str = "",\n''', '''        preferred_storage_key: str = "",\n        preferred_storage_keys: Sequence[str] = (),\n''')
s = s.replace('''        preferred = str(preferred_storage_key or "")\n        if preferred and preferred in accepted_claims and preferred not in selected:\n            selected.append(preferred)\n\n''', '''        preferred_values = [str(preferred_storage_key or "")]\n        preferred_values.extend(str(item or "") for item in preferred_storage_keys)\n        for preferred in preferred_values:\n            if preferred and preferred in accepted_claims and preferred not in selected:\n                selected.append(preferred)\n\n''')
svc.write_text(s, encoding='utf-8')
