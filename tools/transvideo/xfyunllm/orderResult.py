import json
import re


def _loads_json_maybe_escaped(value):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return json.loads(re.sub(r"\\\\", r"\\", value))


def _words_from_st(st):
    words = []
    for rt_item in st.get("rt", []):
        for ws_item in rt_item.get("ws", []):
            cw_items = ws_item.get("cw") or []
            if cw_items:
                words.append(cw_items[0].get("w", ""))
    return "".join(words).strip()


def parse_segments(api_response):
    """Return timestamped ASR segments from an Iflytek API response."""
    order_result_str = api_response.get("content", {}).get("orderResult", "{}")
    order_result = _loads_json_maybe_escaped(order_result_str)

    segments = []
    for lattice_item in order_result.get("lattice", []):
        json_1best = _loads_json_maybe_escaped(lattice_item.get("json_1best", "{}"))
        st = json_1best.get("st", {})
        text = _words_from_st(st)
        if not text:
            continue
        segments.append(
            {
                "begin_ms": int(st.get("bg") or 0),
                "end_ms": int(st.get("ed") or 0),
                "role": str(st.get("rl") or "1"),
                "text": text,
            }
        )
    return segments


def parse_order_result(api_response):
    """Backward-compatible helper: concatenate all recognized text."""
    return "".join(segment["text"] for segment in parse_segments(api_response))
