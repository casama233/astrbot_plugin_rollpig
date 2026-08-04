from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "scripts/apply_authenticated_admin_ui_v310.py"
text = path.read_text(encoding="utf-8")
text = text.replace(
    '"scripts": {"test": "node --test tests/browser/*.test.mjs"}',
    '"scripts": {"test": "node --test --test-timeout=15000 tests/browser/*.test.mjs"}',
)
replacements = {
    "test('core overview and catalog remain usable when authenticated enhancement loading fails', async () => {\n  const {window} = createDom({assetFailure: true});":
    "test('core overview and catalog remain usable when authenticated enhancement loading fails', async t => {\n  const {dom, window} = createDom({assetFailure: true});\n  t.after(() => dom.window.close());",
    "test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async () => {\n  const {window, calls} = createDom();":
    "test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async t => {\n  const {dom, window, calls} = createDom();\n  t.after(() => dom.window.close());",
    "test('analytics API failure stays inside the analytics card and does not break the core page', async () => {\n  const {window} = createDom({analyticsFailure: true});":
    "test('analytics API failure stays inside the analytics card and does not break the core page', async t => {\n  const {dom, window} = createDom({analyticsFailure: true});\n  t.after(() => dom.window.close());",
    "test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async () => {\n  const {window} = createDom();":
    "test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async t => {\n  const {dom, window} = createDom();\n  t.after(() => dom.window.close());",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"browser test cleanup anchor missing: {old[:80]}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
Path(__file__).unlink(missing_ok=True)
print("v3.1.0 jsdom cleanup patched")
