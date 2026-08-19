from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "pages/pig-manager-ex/index.html").read_text(encoding="utf-8")
BACKEND = (ROOT / "ex_admin_feature.py").read_text(encoding="utf-8")


def test_stage2_preview_has_chat_card_compare_and_lightbox_contract():
    assert 'class="chat-card chat-card-ex"' in PAGE
    assert 'data-effective-card-image' in PAGE
    assert 'data-base-card-image' in PAGE
    assert '真实发送 renderer' in PAGE
    assert 'data-compare-toggle' in PAGE
    assert 'data-base-card' in PAGE
    assert 'data-effective-zoom' in PAGE
    assert 'data-base-zoom' in PAGE
    assert 'id="imageLightbox"' in PAGE
    assert "function openLightbox" in PAGE
    assert "function closeLightbox" in PAGE
    assert "@media(max-width:760px)" in PAGE


def test_base_comparison_uses_read_only_production_card_mode():
    assert 'payload.get("base") is True' in BACKEND
    assert "self.render_pig_image(display)" in BACKEND
    assert "post('ex/variants/card',{id:p.id,level,base:true})" in PAGE
    assert "Base · 真实发送 renderer" in PAGE


def test_comparison_is_lazy_and_does_not_mutate_ex_state():
    assert "if(card.dataset.baseLoaded==='1')return" in PAGE
    assert "card.dataset.baseLoaded='1'" in PAGE
    assert "loadBaseCard(card,p)" in PAGE
    assert "Base ↔ EX 对比" in PAGE


def test_preview_does_not_duplicate_production_card_anatomy_in_html():
    assert '<div class="chat-body">' not in PAGE
    assert "data-effective-image" not in PAGE
    assert "ex/variants/card" in PAGE
