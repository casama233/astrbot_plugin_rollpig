from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "pages/pig-manager-ex/index.html").read_text(encoding="utf-8")
BACKEND = (ROOT / "ex_admin_feature.py").read_text(encoding="utf-8")


def test_stage2_preview_has_chat_card_compare_and_lightbox_contract():
    assert 'class="chat-card chat-card-ex"' in PAGE
    assert 'data-compare-toggle' in PAGE
    assert 'data-base-card' in PAGE
    assert 'data-effective-zoom' in PAGE
    assert 'data-base-zoom' in PAGE
    assert 'id="imageLightbox"' in PAGE
    assert "function openLightbox" in PAGE
    assert "function closeLightbox" in PAGE
    assert "@media(max-width:760px)" in PAGE


def test_base_comparison_uses_read_only_base_image_mode():
    assert 'payload.get("base") is True' in BACKEND
    assert "path = self.find_image_file(pig_id)" in BACKEND
    assert "post('ex/variants/image',{id:p.id,level,base:true})" in PAGE
    assert "Base · 未套 EX" in PAGE


def test_comparison_is_lazy_and_does_not_mutate_ex_state():
    assert "if(card.dataset.baseLoaded==='1')return" in PAGE
    assert "card.dataset.baseLoaded='1'" in PAGE
    assert "loadBaseImage(card,p)" in PAGE
    assert "Base ↔ EX 對比" in PAGE
