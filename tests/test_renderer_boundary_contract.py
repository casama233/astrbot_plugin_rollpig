import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER_FILES = (
    ROOT / "renderers" / "common.py",
    ROOT / "renderers" / "pig_card.py",
    ROOT / "renderers" / "catalog.py",
    ROOT / "renderers" / "roast.py",
    ROOT / "renderers" / "weekly.py",
)


def _method(tree: ast.AST, class_name: str, method_name: str):
    cls = next(
        node
        for node in getattr(tree, "body", [])
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    )


def test_renderer_modules_have_no_runtime_or_storage_dependency():
    forbidden = {
        "AstrMessageEvent",
        "astrbot",
        "storage",
        "save_json",
        "save_json_batch",
        "load_json",
        "_get_user_collection",
        "_get_weekly_pig",
        "_today",
        "sync_cloud_resources",
    }
    for path in RENDERER_FILES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert not (forbidden & (names | attrs | imported)), path.name


def test_legacy_render_facades_do_not_draw_directly():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    expected_delegate = {
        "render_pig_image": "render_pig_card",
        "render_pigsty_image": "render_pigsty",
        "render_catalog_grid": "render_catalog_grid_image",
        "render_roast_image": "render_roast_card_image",
        "render_weekly_summary": "render_weekly_summary_image",
    }
    forbidden_draw_names = {"PILImage", "ImageDraw", "ImageOps", "tempfile"}
    for method_name, delegate in expected_delegate.items():
        method = _method(tree, "RollPigPlugin", method_name)
        names = {node.id for node in ast.walk(method) if isinstance(node, ast.Name)}
        calls = {
            node.func.id
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not (forbidden_draw_names & names), method_name
        assert delegate in calls, method_name


def test_weekly_domain_read_stays_in_legacy_facade_only():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = _method(tree, "RollPigPlugin", "render_weekly_summary")
    attrs = {node.attr for node in ast.walk(method) if isinstance(node, ast.Attribute)}
    assert "_get_weekly_pig" in attrs

    renderer = ast.parse((ROOT / "renderers" / "weekly.py").read_text(encoding="utf-8"))
    renderer_attrs = {
        node.attr for node in ast.walk(renderer) if isinstance(node, ast.Attribute)
    }
    assert "_get_weekly_pig" not in renderer_attrs
