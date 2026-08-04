import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "scripts/apply_authenticated_admin_ui_v310.py"
text = path.read_text(encoding="utf-8")

# Browser tests must be bounded and must close each jsdom window cleanly.
text = text.replace(
    '"scripts": {"test": "node --test tests/browser/*.test.mjs"}',
    '"scripts": {"test": "node --test --test-timeout=15000 tests/browser/*.test.mjs"}',
)
replacements = {
    "test('core overview and catalog remain usable when authenticated enhancement loading fails', async () => {\n  const {window} = createDom({assetFailure: true});":
    "test('core overview and catalog remain usable when authenticated enhancement loading fails', async t => {\n  const {dom, window} = createDom({assetFailure: true});\n  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });",
    "test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async () => {\n  const {window, calls} = createDom();":
    "test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async t => {\n  const {dom, window, calls} = createDom();\n  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });",
    "test('analytics API failure stays inside the analytics card and does not break the core page', async () => {\n  const {window} = createDom({analyticsFailure: true});":
    "test('analytics API failure stays inside the analytics card and does not break the core page', async t => {\n  const {dom, window} = createDom({analyticsFailure: true});\n  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });",
    "test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async () => {\n  const {window} = createDom();":
    "test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async t => {\n  const {dom, window} = createDom();\n  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"browser test cleanup anchor missing: {old[:80]}")
    text = text.replace(old, new, 1)

# Keep dependencies out of the product commit. The permanent frontend CI job is
# added separately after the validated product commit, because the temporary
# GitHub App token cannot modify workflow files.
text, count = re.subn(
    r"\n# Permanent CI gains an independent browser behavior job\..*?write\(\"\.github/workflows/ci\.yml\", ci\)\n",
    "\n# Permanent frontend CI is installed separately after this validated commit.\n",
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("permanent CI mutation block not found")

# Make the enterprise observer lifecycle-safe for AstrBot SPA page replacement
# and for browser test teardown.
enterprise_anchor = 'enterprise = read("pages/pig-manager/ui-enterprise.js")\n'
enterprise_patch = '''enterprise = read("pages/pig-manager/ui-enterprise.js")
enterprise = enterprise.replace(
    "  const syncBusyState = () => {\\n    const busy = Boolean(document.querySelector('[aria-busy=\\\"true\\\"],.loading.show'));",
    "  const syncBusyState = () => {\\n    if (!document?.body) return;\\n    const busy = Boolean(document.querySelector('[aria-busy=\\\"true\\\"],.loading.show'));",
    1,
)
'''
if enterprise_anchor not in text:
    raise SystemExit("enterprise source anchor missing")
text = text.replace(enterprise_anchor, enterprise_patch, 1)

refresh_old = '''    "  window.__rollpigEnterpriseUiRefresh = () => {\\n    addSkipLink();\\n    decorateStructure();\\n    syncBusyState();\\n  };\\n  window.__rollpigEnterpriseUiRefresh();",'''
refresh_new = '''    "  window.__rollpigEnterpriseUiRefresh = () => {\\n    if (!document?.body) return;\\n    addSkipLink();\\n    decorateStructure();\\n    syncBusyState();\\n  };\\n  window.__rollpigEnterpriseUiRefresh();\\n  window.addEventListener('pagehide', () => {\\n    observer.disconnect();\\n    window.__rollpigEnterpriseUiReady = false;\\n    window.__rollpigEnterpriseUiRefresh = null;\\n  }, {once: true});",'''
if refresh_old not in text:
    raise SystemExit("enterprise refresh replacement anchor missing")
text = text.replace(refresh_old, refresh_new, 1)

path.write_text(text, encoding="utf-8")
Path(__file__).unlink(missing_ok=True)
print("v3.1.0 browser cleanup and workflow isolation patched")
