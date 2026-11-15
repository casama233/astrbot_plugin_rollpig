# Exact phrases from superseded copy are not a behavior contract. Retain the
# observed image/fact exclusions and resource checks across creative rewrites.
from __future__ import annotations
import json
from pathlib import Path
import pytest
from PIL import Image
from bundled_ex_copy import load_bundled_ex_copy
ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / 'resource'

@pytest.fixture(scope='module')
def variants():
    pig_ids = set(_catalog_by_id())
    return load_bundled_ex_copy(RESOURCE_DIR, pig_ids, pig_ids, image_extensions={'png', 'jpg', 'jpeg', 'webp', 'gif'})

def _catalog() -> list[dict]:
    return json.loads((RESOURCE_DIR / 'pig.json').read_text(encoding='utf-8-sig'))

def _catalog_by_id() -> dict[str, dict]:
    return {str(item.get('id') or ''): item for item in _catalog() if isinstance(item, dict) and str(item.get('id') or '')}

def _copy(variants, pig_id: str) -> str:
    return ''.join((variants[pig_id][level]['description'] + variants[pig_id][level]['analysis'] for level in range(1, 6)))

def test_phase10_visual_research_and_safety_boundaries_remain_explicit(variants):
    porkchop = _copy(variants, 'mc_porkchop')
    assert '恢复生命值' not in porkchop
    pig_god = _copy(variants, 'pig_god')
    assert all((token not in pig_god for token in ('祥云', '莲台', '宙斯', '雅典娜')))
    tank = _copy(variants, 'tank_pig')
    assert all((token not in tank for token in ('肥婆', '胖女人', '坦克女', '母坦克')))
    veteran = _copy(variants, 'lao_zhu_li')
    assert all((token not in veteran for token in ('题库', '刷题', '考试答案')))
    invisible = _copy(variants, 'invisible_pig')
    assert '只剩一点若隐若现的猪鼻子' not in invisible
    buddha = _copy(variants, 'buddha-pig')
    assert all((token not in buddha for token in ('迷信', '骗钱', '装神弄鬼')))
    frozen = _copy(variants, 'frozen-pig')
    assert '微波' not in frozen

def test_phase11_visual_wordplay_and_food_research_boundaries_remain_explicit(variants):
    pearl = _copy(variants, 'pearl-pig')
    assert '你把一颗硕大的珍珠顶在身上' not in pearl
    chocolate = _copy(variants, 'chocolate-pig')
    assert '喂猪吃巧克力' not in chocolate
    jewelry = _copy(variants, 'jewelry-pig')
    assert '从耳朵到尾巴挂满珠宝' not in jewelry
    suckling = _copy(variants, 'suckling-pig')
    assert '二至六个星期' not in suckling

def test_phase12_visual_wordplay_food_and_brand_boundaries_remain_explicit(variants):
    everest = _copy(variants, 'everest-pig')
    assert all((token not in everest for token in ('登顶尸体', '遇难者', '插旗')))
    burger = _copy(variants, 'burger-pig')
    assert all((token not in burger for token in ('牛肉饼', '鸡肉饼')))
    chef = _copy(variants, 'chef-pig')
    assert '刀工精湛' not in chef
    house = _copy(variants, 'prison-break-pig')
    assert all((token not in house for token in ('越狱成功', '牢房', '狱警')))
    milk = _copy(variants, 'pig-skin-milk')
    assert all((token not in milk for token in ('加入真实猪皮', '配料含猪皮', '用猪皮制作')))
    lard = _copy(variants, 'lard-pig')
    assert all((token not in lard for token in ('更健康', '营养价值', '减肥')))
    sushi = _copy(variants, 'salmon-sushi-pig')
    assert all((token not in sushi for token in ('可以直接生食', '保证生食安全', '现切鱼片上桌')))

def test_mini_pig_copy_matches_current_transparent_asset_geometry():
    with Image.open(RESOURCE_DIR / 'image' / 'mini-pig.png') as image:
        rgba = image.convert('RGBA')
        assert rgba.size == (240, 240)
        assert rgba.getchannel('A').getbbox() == (102, 112, 138, 144)

def test_phase13_visual_wordplay_research_and_safety_boundaries_remain_explicit(variants):
    upper = _copy(variants, 'upper-class-pig')
    assert all((token not in upper for token in ('刀叉', '燕尾服')))
    alien = _copy(variants, 'alien-pig')
    assert all((token not in alien for token in ('外星人IP', '某作品角色', '飞碟驾驶员')))
    antibacterial = _copy(variants, 'antibacterial-pig')
    assert all((token not in antibacterial for token in ('已证实杀菌率', '真实杀菌率99.9%', '可预防疾病', '医疗功效')))
    pigskin = _copy(variants, 'pigskin-pig')
    assert all((token not in pigskin for token in ('自杀', '尸体', '死亡', '上吊')))
    elephant = _copy(variants, 'elephant-pig')
    assert all((token not in elephant for token in ('披上灰色象皮', '扇动大耳朵', '真正象鼻')))
    hanging = _copy(variants, 'hanging-pig')
    assert all((token not in hanging for token in ('吊着吊着就习惯了', '上吊练习', '悬空很舒服', '继续晃两下')))

def test_phase13_repairs_materially_inaccurate_elephant_and_hanging_base_copy():
    catalog = _catalog_by_id()
    elephant = catalog['elephant-pig']
    assert elephant['name'] == '装象猪'
    assert all((token not in elephant['analysis'] for token in ('披上灰色象皮', '扇动大耳朵', '长出大耳朵')))
    hanging = catalog['hanging-pig']
    assert hanging['name'] == '吊运猪'
    assert all((token not in hanging['analysis'] for token in ('再晃两下', '上吊猪')))

def test_all_bundled_authored_copy_is_globally_unique(variants):
    catalog_ids = set(_catalog_by_id())
    assert set(variants) == catalog_ids
    assert len(variants) == 99
    descriptions = [levels[level]['description'] for levels in variants.values() for level in range(1, 6)]
    analyses = [levels[level]['analysis'] for levels in variants.values() for level in range(1, 6)]
    assert len(descriptions) == len(set(descriptions)) == 495
    assert len(analyses) == len(set(analyses)) == 495

def test_phase8_research_boundaries_remain_visible_in_copy(variants):
    assert '初音' not in ''.join((item['analysis'] for item in variants['doll-pig'].values()))
    combined_black_white = ''.join((item['description'] + item['analysis'] for item in variants['black-white-pig'].values()))
    assert 'Monokuro' not in combined_black_white
    assert 'San-X' not in combined_black_white

def test_phase9_visual_and_reference_boundaries_remain_explicit(variants):
    rainbow = _copy(variants, 'rainbow-pig')
    assert all((token not in rainbow for token in ('Stuart Little', 'LGBT', '骄傲月', '检索不到')))
    pig_bun = _copy(variants, 'pig-bun')
    assert '猪肉馅' not in pig_bun
    crown = _copy(variants, 'chained_crown_pig')
    assert '莎士比亚' not in crown
    vangogh = _copy(variants, 'vangogh_pig')
    assert all((token not in vangogh for token in ('精神病', '疯子', '发疯')))
