from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

try:
    import astrbot.api  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )
    web_module = types.ModuleType("astrbot.api.web")
    web_module.request = types.SimpleNamespace()
    astrbot_module.api = api_module
    sys.modules.setdefault("astrbot", astrbot_module)
    sys.modules.setdefault("astrbot.api", api_module)
    sys.modules.setdefault("astrbot.api.web", web_module)

from ex_public_source_feature import ExPublicSourceMixin


class _Harness(ExPublicSourceMixin):
    def __init__(self):
        self.sent = None

    def _public_source_submission_payload(self, pig_id: str):
        return (
            {
                "id": pig_id,
                "name": "Rights Pig",
                "description": "rights-v3",
                "analysis": "rights-aware submission",
            },
            b"base-image",
        )

    async def _public_source_request_json(
        self, method: str, path: str, *, payload=None, admin: bool = False
    ):
        self.sent = {
            "method": method,
            "path": path,
            "payload": payload,
            "admin": admin,
        }
        return {
            "submission_id": "a" * 32,
            "status": "pending",
            "publication_status": "not_published",
        }


def _rights(**updates):
    value = {
        "basis": "original",
        "author": "Example Author",
        "rights_holder": "Example Author",
        "source_url": "https://example.com/original/rights-pig",
        "license_id": "",
        "permission_evidence_url": "",
        "attribution": "Example Author — original submission",
        "notes": "",
        "redistribution_authorized": True,
        "attestation": True,
    }
    value.update(updates)
    return value


def test_regular_public_source_submission_uses_rights_v3():
    app = _Harness()
    rights = app._normalize_public_source_rights(_rights())

    result = asyncio.run(app._submit_local_pig_to_public_source("rights-pig", rights))

    assert result["publication_status"] == "not_published"
    assert app.sent["method"] == "POST"
    assert app.sent["path"] == "/submissions"
    assert app.sent["payload"]["submission_version"] == 3
    assert app.sent["payload"]["rights"] == rights
    assert app.sent["payload"]["record"]["id"] == "rights-pig"


def test_license_and_explicit_permission_fail_closed_without_evidence():
    with pytest.raises(ValueError):
        _Harness._normalize_public_source_rights(_rights(basis="license"))

    with pytest.raises(ValueError):
        _Harness._normalize_public_source_rights(
            _rights(basis="explicit_permission")
        )

    licensed = _Harness._normalize_public_source_rights(
        _rights(basis="license", license_id="CC-BY-4.0")
    )
    assert licensed["license_id"] == "CC-BY-4.0"

    permitted = _Harness._normalize_public_source_rights(
        _rights(
            basis="explicit_permission",
            permission_evidence_url="https://example.com/permission/123",
        )
    )
    assert permitted["permission_evidence_url"].startswith("https://")


def test_rights_attestations_must_be_literal_true():
    with pytest.raises(ValueError):
        _Harness._normalize_public_source_rights(
            _rights(redistribution_authorized="true")
        )
    with pytest.raises(ValueError):
        _Harness._normalize_public_source_rights(_rights(attestation=1))


def test_main_manager_loads_rights_integration_without_dropping_ex_manager():
    root = Path(__file__).resolve().parents[1]
    wrapper = (root / "pages/pig-manager/ex-integration.js").read_text(encoding="utf-8")
    rights_ui = (root / "pages/pig-manager/rights-integration.js").read_text(encoding="utf-8")

    assert "import './ex-integration-core.js'" in wrapper
    assert "import './rights-integration.js'" in wrapper
    assert "rights_verified" in rights_ui
    assert "redistribution_authorized" in rights_ui
    assert "permission_evidence_url" in rights_ui
    assert "审核通过不会自动发布" in rights_ui
    assert "[data-review-approve]" in rights_ui
    assert "[data-submit]" in rights_ui


def test_legacy_ex_public_source_page_no_longer_claims_approval_publishes():
    root = Path(__file__).resolve().parents[1]
    page = (root / "pages/pig-manager-ex-public-source/index.html").read_text(
        encoding="utf-8"
    )
    assert "旧 envelope v2" in page
    assert "管理员审核通过也不会自动发布" in page
    assert "批准并发布" not in page
    assert "apiPost" not in page
