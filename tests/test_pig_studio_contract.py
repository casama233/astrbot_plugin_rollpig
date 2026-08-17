from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_pig_studio_is_wired_through_secure_admin_layer():
    source = read("main.py")
    assert "from .pig_studio_admin import PigStudioAdminMixin" in source
    assert "from .pig_studio_feature import PigStudioMixin" in source
    assert source.index("    PigStudioAdminMixin,") < source.index("    PigStudioMixin,")


def test_pig_studio_registers_authenticated_write_apis():
    feature = read("pig_studio_feature.py")
    admin = read("pig_studio_admin.py")
    for route in ("studio/plan", "studio/render", "studio/import"):
        assert route in feature
    assert "studio/config" in admin
    assert feature.count("_is_authorized_write_request(request, payload)") >= 3
    assert "_is_authorized_write_request(request, payload)" in admin


def test_pig_studio_reuses_astrbot_provider_for_planning():
    source = read("pig_studio_feature.py")
    assert "self.context.get_using_provider()" in source
    assert "provider.text_chat(" in source
    assert "image_urls=[]" in source


def test_pig_studio_keeps_full_generated_images_server_side_until_import():
    source = read("pig_studio_feature.py")
    assert 'self.plugin_data_dir / "pig_studio_drafts"' in source
    assert '"draft_id": draft_id' in source
    assert '"preview": preview' in source
    assert "_studio_preview" in source
    assert "_persist_catalog_override(record, normalized)" in source
    assert "该小猪 ID 已存在；AI 工坊只允许新增" in source


def test_pig_studio_status_never_returns_the_stored_api_key():
    source = read("pig_studio_admin.py")
    start = source.index("    def _studio_status_payload")
    end = source.index("    async def page_studio_status", start)
    status_block = source[start:end]
    assert '"api_key_present": bool(self.pig_studio_image_api_key)' in status_block
    assert '"api_key":' not in status_block
    assert '"api_key": self.pig_studio_image_api_key' not in source


def test_pig_studio_remote_generated_image_fetch_is_same_host_only():
    source = read("pig_studio_admin.py")
    start = source.index("    async def _studio_download_generated_url")
    block = source[start:]
    assert 'parsed.scheme != "https"' in block
    assert '(parsed.hostname or "").lower() != (base.hostname or "").lower()' in block
    assert "follow_redirects=False" in block
    assert "非同源图片地址" in block
    assert "os.environ" not in read("pig_studio_feature.py")
    assert "os.environ" not in source


def test_pig_studio_base_url_rejects_plain_http_except_loopback():
    source = read("pig_studio_admin.py")
    assert 'host in {"localhost", "127.0.0.1", "::1"}' in source
    assert 'parsed.scheme != "https"' in source
    assert 'parsed.scheme == "http" and loopback' in source


def test_pig_manager_bootstrap_loads_the_studio_without_new_plugin_page():
    bootstrap = read("pages/pig-manager/ui-bootstrap.js")
    studio = read("pages/pig-manager/studio-integration.js")
    assert "studio-integration.js" in bootstrap
    assert "data-rollpig-pig-studio-loader" in bootstrap
    assert "AI 小猪工坊" in studio
    assert "studio/status" in studio
    assert "studio/plan" in studio
    assert "studio/render" in studio
    assert "studio/import" in studio
    assert "studio/config" in studio


def test_pig_studio_frontend_never_requests_stored_key_back():
    source = read("pages/pig-manager/studio-integration.js")
    assert "api_key_present" in source
    assert "留空＝保留服务端现有 Key" in source
    assert "studioApiKey').value = ''" in source
    assert "image_b64" not in source


def test_pig_studio_records_autopig_inspiration_without_copying_runtime_model():
    source = read("pig_studio_feature.py")
    assert "AutoPig-Studio" in source
    assert "MIT" in source
    assert "native to RollPig" in source
    assert "FastAPI" not in source
    assert "CORSMiddleware" not in source
