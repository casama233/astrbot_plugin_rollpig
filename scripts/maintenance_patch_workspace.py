"""Read-only inspection for a temporary branch-scoped maintenance workspace."""
import ast
from pathlib import Path

for filename, names in {
    'legacy_main.py': {'sync_cloud_resources', '_cloud_state', '_save_sync_status'},
    'storage/sqlite_storage.py': {'__init__', '_initialize'},
    'storage/primary_manager.py': {'_select_initial_backend'},
}.items():
    source = Path(filename).read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            print(f'\n=== {filename}:{node.lineno} {node.name} ===\n')
            print(ast.get_source_segment(source, node))

page = Path('pages/pig-manager/index.html').read_text(encoding='utf-8').splitlines()
for index, line in enumerate(page):
    if 'function renderResourceStatus' in line:
        print('\n=== renderResourceStatus ===\n')
        print('\n'.join(page[index:index + 50]))
for filename in ['tests/test_resource_failover.py', 'tests/test_reviewed_mirror.py', 'tests/test_legacy_shrink_budget.py', 'package.json']:
    print(f'\n=== {filename} ===\n')
    print(Path(filename).read_text(encoding='utf-8'))
