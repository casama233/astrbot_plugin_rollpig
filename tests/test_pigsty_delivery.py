from __future__ import annotations

import ast
from pathlib import Path

from services.delivery import is_uncertain_send_timeout


ROOT = Path(__file__).resolve().parents[1]


class FakeActionFailed(Exception):
    def __init__(self, result: dict):
        self.result = result
        super().__init__(str(result))


def test_ntqq_sendmsg_timeout_is_uncertain_delivery():
    exc = FakeActionFailed(
        {
            "retcode": 1200,
            "message": (
                "Timeout: NTEvent serviceAndMethod:NodeIKernelMsgService/sendMsg "
                "ListenerName:NodeIKernelMsgListener/onMsgInfoListUpdate"
            ),
            "wording": "Timeout: NodeIKernelMsgService/sendMsg",
        }
    )
    assert is_uncertain_send_timeout(exc) is True


def test_other_send_failures_are_not_treated_as_delivered():
    assert (
        is_uncertain_send_timeout(
            FakeActionFailed({"retcode": 100, "message": "sendMsg failed"})
        )
        is False
    )
    assert (
        is_uncertain_send_timeout(
            FakeActionFailed({"retcode": 1200, "message": "request timeout"})
        )
        is False
    )
    assert (
        is_uncertain_send_timeout(
            FakeActionFailed({"retcode": 1200, "message": "sendMsg rejected"})
        )
        is False
    )


def test_pigsty_handler_separates_render_and_delivery_failures():
    source = (ROOT / "permanent_collection_feature.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    handler = functions["my_pigsty"]
    handler_source = ast.get_source_segment(source, handler) or ""

    assert "is_uncertain_send_timeout(exc)" in handler_source
    assert "消息可能已成功投递" in handler_source
    assert "图鉴已生成，但图片发送失败" in handler_source
    assert "图鉴图片生成失败" in handler_source
    assert "page_count(display_catalog)" in handler_source
    assert "page_count(self.pig_list)" not in handler_source
