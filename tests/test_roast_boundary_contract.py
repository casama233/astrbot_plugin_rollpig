import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _class_method(path: str, class_name: str, method_name: str):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    )


def _defined_methods(path: str, class_name: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _call_chain(call: ast.Call) -> str:
    node = call.func
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def test_daily_report_observes_roasts_without_owning_the_flow():
    methods = _defined_methods("daily_report_feature.py", "DailyReportMixin")
    assert "_roast_group_target" not in methods
    assert "_record_roast_outcome_event" in methods


def test_normal_roast_flow_uses_service_policy_and_event_hook():
    method = _class_method("legacy_main.py", "RollPigPlugin", "_roast_group_target")
    calls = {_call_chain(node) for node in ast.walk(method) if isinstance(node, ast.Call)}
    assert "self.roast_service.choose_group_roast_outcome" in calls
    assert "self._record_roast_outcome_event" in calls
    assert "random.choices" not in calls


def test_reservation_uses_same_outcome_policy():
    source = (ROOT / "roast_reservation_feature.py").read_text(encoding="utf-8")
    assert "random.choices" not in source
    assert "roast_service.choose_group_roast_outcome" in source


def test_roast_renderer_has_no_plugin_runtime_or_storage_dependency():
    source = (ROOT / "renderers" / "roast.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "AstrMessageEvent",
        "astrbot",
        "storage",
        "load_json",
        "save_json",
        "_today",
        "_get_daily_pig",
        "roast_service",
    }
    assert not (forbidden & (names | attrs | imported))


def test_legacy_roast_renderer_is_only_a_facade():
    method = _class_method("legacy_main.py", "RollPigPlugin", "render_roast_image")
    calls = {_call_chain(node) for node in ast.walk(method) if isinstance(node, ast.Call)}
    names = {node.id for node in ast.walk(method) if isinstance(node, ast.Name)}
    assert "render_roast_card_image" in calls
    assert not ({"PILImage", "ImageDraw", "ImageOps", "tempfile"} & names)
