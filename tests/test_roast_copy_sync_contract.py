from pathlib import Path


def test_resource_sync_supports_optional_roast_copy_pack():
    source = Path("legacy_main.py").read_text(encoding="utf-8")
    assert 'roast_copy_meta = manifest.get("roast_copy")' in source
    assert 'manifest roast_copy 必须是对象' in source
    assert 'validate_roast_copy_catalog(' in source
    assert '(staging / "roast_copy.json").write_bytes(roast_copy_raw)' in source
    assert 'package_total = len(pig_raw) + len(ex_raw) + len(roast_copy_raw)' in source
    assert 'not isinstance(manifest.get("roast_copy"), dict)' in source
    assert '(self.resource_active_dir / "roast_copy.json").is_file()' in source


def test_ai_roast_prompt_and_cache_contract_are_piggish_and_multi_candidate():
    source = Path("legacy_main.py").read_text(encoding="utf-8")
    assert "一次生成4条彼此明显不同" in source
    assert "猪圈、猪籍、猪运、返场、EX、Charge、烤架、保底、拱、哼哼、后厨" in source
    assert "外焦里嫩、香气扑鼻、火候刚好、入口即化、肥而不腻" in source
    assert "f\"图鉴文案：{str(pig.get('analysis')" in source
    assert "encode_ai_candidates(candidates[:4])" in source
    assert "decode_ai_candidates(payload)" in source
    assert "self._select_ai_from_recent(event, recent)" in source


def test_roast_card_no_longer_uses_five_fixed_recipes():
    renderer = Path("renderers/roast.py").read_text(encoding="utf-8")
    assert "RECIPES =" not in renderer
    assert "local_copy: Mapping[str, object] | None" in renderer
    assert 'recipe = "AI 豬圈私房"' in renderer
