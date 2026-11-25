from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from .display_copy import simplify_display_text
except ImportError:  # pragma: no cover - direct module loading compatibility
    from display_copy import simplify_display_text

SCHEMA_VERSION = 1
MAX_PACK_BYTES = 256 * 1024
MIN_DISH_NAMES = 24
MIN_LINES = 64
RECENT_HISTORY_LIMIT = 24
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


def validate_roast_copy_catalog(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping) or int(raw.get("schema_version") or 0) != SCHEMA_VERSION:
        raise ValueError("roast_copy schema_version must be 1")
    dishes = raw.get("dish_names")
    lines = raw.get("lines")
    if not isinstance(dishes, list) or len(dishes) < MIN_DISH_NAMES:
        raise ValueError(f"roast_copy requires at least {MIN_DISH_NAMES} dish names")
    if not isinstance(lines, list) or len(lines) < MIN_LINES:
        raise ValueError(f"roast_copy requires at least {MIN_LINES} copy lines")
    normalized_dishes = [str(item).strip() for item in dishes]
    normalized_lines = [str(item).strip() for item in lines]
    if any(not item or len(item) > 24 for item in normalized_dishes):
        raise ValueError("roast_copy dish name length is invalid")
    if any(not item or len(item) > 120 for item in normalized_lines):
        raise ValueError("roast_copy line length is invalid")
    if len(set(normalized_dishes)) != len(normalized_dishes):
        raise ValueError("roast_copy dish names must be unique")
    if len(set(normalized_lines)) != len(normalized_lines):
        raise ValueError("roast_copy lines must be unique")
    for line in normalized_lines:
        unknown = set(_PLACEHOLDER.findall(line)).difference({"pig"})
        if unknown:
            raise ValueError(
                "roast_copy line has unknown placeholder: "
                + ", ".join(sorted(unknown))
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "dish_names": normalized_dishes,
        "lines": normalized_lines,
    }


def load_roast_copy_catalog(path: Path) -> dict[str, object]:
    path = Path(path)
    if path.stat().st_size > MAX_PACK_BYTES:
        raise ValueError("roast_copy pack exceeds 256 KiB")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read roast_copy pack: {exc}") from exc
    return validate_roast_copy_catalog(raw)


def select_local_roast_copy(
    catalog: Mapping[str, object],
    *,
    pig_name: str,
    recent_keys: Iterable[str] = (),
    rng: random.Random | random.SystemRandom | None = None,
) -> dict[str, str]:
    validated = validate_roast_copy_catalog(catalog)
    dishes: list[str] = list(validated["dish_names"])  # type: ignore[arg-type]
    lines: list[str] = list(validated["lines"])  # type: ignore[arg-type]
    blocked = set(list(recent_keys)[-RECENT_HISTORY_LIMIT:])
    picker = rng or random

    selected: tuple[int, int] | None = None
    for _ in range(64):
        dish_index = picker.randrange(len(dishes))
        line_index = picker.randrange(len(lines))
        key = f"local:{dish_index}:{line_index}"
        if key not in blocked:
            selected = (dish_index, line_index)
            break
    if selected is None:
        for dish_index in range(len(dishes)):
            for line_index in range(len(lines)):
                if f"local:{dish_index}:{line_index}" not in blocked:
                    selected = (dish_index, line_index)
                    break
            if selected is not None:
                break
    if selected is None:
        selected = (picker.randrange(len(dishes)), picker.randrange(len(lines)))

    dish_index, line_index = selected
    key = f"local:{dish_index}:{line_index}"
    copy = lines[line_index].format(
        pig=simplify_display_text(pig_name or "小猪")[:30]
    )
    return {"dish": dishes[dish_index], "copy": copy, "key": key}


def decode_ai_candidates(payload: object) -> list[str]:
    text = str(payload or "").strip()
    if not text:
        return []
    values: Sequence[object]
    try:
        decoded = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        decoded = None
    values = decoded if isinstance(decoded, list) else [text]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        candidate = re.sub(r"\s+", " ", simplify_display_text(item)).strip(
            "“”\"'` "
        )[:64]
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
    return result


def encode_ai_candidates(candidates: Sequence[str]) -> str:
    normalized = decode_ai_candidates(
        json.dumps(list(candidates), ensure_ascii=False)
    )
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def ai_candidate_key(text: str) -> str:
    normalized = simplify_display_text(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"ai:{digest}"


def select_ai_candidate(
    candidates: Sequence[str],
    *,
    recent_keys: Iterable[str] = (),
    rng: random.Random | random.SystemRandom | None = None,
) -> str | None:
    normalized = decode_ai_candidates(
        json.dumps(list(candidates), ensure_ascii=False)
    )
    if not normalized:
        return None
    blocked = set(list(recent_keys)[-RECENT_HISTORY_LIMIT:])
    available = [
        item for item in normalized if ai_candidate_key(item) not in blocked
    ]
    picker = rng or random
    return picker.choice(available or normalized)


def build_roast_copy_prompt(pig: Mapping[str, object]) -> str:
    return (
        "你是‘今日小猪’猪圈宇宙的后厨总编，不是普通美食博主。"
        "一次生成4条彼此明显不同的中文烤猪卡文案，并只输出JSON字符串数组。"
        "每条18-42个汉字，必须有猪言猪语和反差包袱，自然带入至少一个猪圈世界观元素："
        "猪圈、猪籍、猪运、返场、EX、Charge、烤架、保底、拱、哼哼、后厨。"
        "四条分别偏向：猪圈黑话、抽卡命运、后厨判词、哲学反转；不要只是换同义词。"
        "禁止写成普通美食广告；除非用于反转，不要使用‘外焦里嫩、香气扑鼻、火候刚好、入口即化、肥而不腻’套话。"
        f"小猪名：{str(pig.get('name') or '小猪')[:30]}；"
        f"描述：{str(pig.get('description') or '')[:100]}；"
        f"图鉴文案：{str(pig.get('analysis') or '')[:180]}。"
        "只调侃虚构小猪、猪圈日常和抽卡命运；禁止针对真实用户或群体，禁止仇恨、性内容、自残、血腥和真实暴力细节；"
        "不写真实烹饪步骤，不解释笑点，不加标题或Markdown。"
        "输出示例格式：[\"第一条\",\"第二条\",\"第三条\",\"第四条\"]"
    )
