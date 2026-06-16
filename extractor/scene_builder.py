import re
from difflib import get_close_matches


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase, strip tags/punctuation, collapse spaces."""
    text = text.lower()
    text = re.sub(r"[:\|\-]", " ", text)   # remove : | -
    text = re.sub(r"\s+", " ", text)         # collapse spaces
    return text.strip()


def _compute_center(bbox: dict) -> dict:
    return {
        "x": round(bbox["x"] + bbox["width"]  / 2, 2),
        "y": round(bbox["y"] + bbox["height"] / 2, 2),
    }


# ---------------------------------------------------------------------------
# Index builder — THREE keys per element for max match coverage
# ---------------------------------------------------------------------------

def build_index(unified: dict) -> tuple[dict, dict, dict]:
    """
    Build 3 complementary indexes:
    - norm_index  : normalize(tag + text)          → primary lookup
    - text_index  : normalize(text only)            → fallback when tag prefix missing
    - y_index     : tag|normalize(text)|y_bucket    → duplicate element resolver
    """
    norm_index = {}
    text_index = {}
    y_index    = {}

    for el in unified["elements"]:
        tag  = el["tag"]
        text = el["text"].strip()
        bbox = el["bbox"]

        # Primary key
        norm_key = normalize(f"{tag} {text}")
        norm_index[norm_key] = el

        # Text-only fallback
        text_key = normalize(text)
        if text_key not in text_index:          # first occurrence wins
            text_index[text_key] = el

        # Y-bucket key — differentiates duplicate text at different positions
        # bucket size = 50px so minor layout shifts don't break match
        if bbox:
            y_bucket = int(bbox["y"] // 50)
            y_key    = f"{tag}|{normalize(text)}|{y_bucket}"
            y_index[y_key] = el
        
    

    return norm_index, text_index, y_index


# ---------------------------------------------------------------------------
# Smart element finder — 4-layer fallback
# ---------------------------------------------------------------------------

def _find_element(
    item: str,
    norm_index: dict,
    text_index: dict,
    y_index: dict,
) -> dict | None:

    # --- Layer 1: normalized exact match (tag + text) ---
    el = norm_index.get(normalize(item))
    if el:
        return el

    # --- Layer 2: strip known tag prefixes, match text only ---
    # Handles "H1: Sumit" → "Sumit", "BUTTON: View Projects" → "View Projects"
    stripped = re.sub(
        r"^(h1|h2|h3|h4|button|link|a)\s*[:\|]?\s*",
        "",
        item,
        flags=re.IGNORECASE,
    ).strip()

    el = text_index.get(normalize(stripped))
    if el:
        return el

    # --- Layer 3: fuzzy match on normalized keys (safe cutoff) ---
    candidates = list(norm_index.keys())
    close = get_close_matches(normalize(item), candidates, n=1, cutoff=0.82)
    if close:
        return norm_index[close[0]]

    # --- Layer 4: fuzzy on text-only index ---
    close = get_close_matches(normalize(stripped), list(text_index.keys()), n=1, cutoff=0.82)
    if close:
        return text_index[close[0]]

    return None


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def attach_coordinates(scenes: dict, unified: dict) -> list[dict]:
    """
    Enrich LLM scene elements with bbox + center from unified extractor output.

    Args:
        scenes:  Output from rank_importance() — {scenes: [...], skipped_noise: [...]}
        unified: Output from extract_website() — {meta, elements}

    Returns:
        List of enriched scenes ready for camera planning / video generation.
    """
    norm_index, text_index, y_index = build_index(unified)
    enriched = []

    for scene in scenes["scenes"]:
        matched   = []
        unmatched = []

        for item in scene["elements"]:
            clean_item = re.sub(r"\(score:\d+\)", "", item).strip()
            clean_item = clean_item.replace("H1 ", "h1: ").replace("H2 ", "h2: ").replace("H3 ", "h3: ")

            el = _find_element(clean_item, norm_index, text_index, y_index)

            if el and el.get("bbox"):
                bbox = el["bbox"]
                matched.append({
                    "text":   el["text"],
                    "tag":    el["tag"],
                    "bbox":   bbox,
                    "center": _compute_center(bbox),
                })
            else:
                unmatched.append(item)

        if unmatched:
            print(f"⚠️  Unmatched in '{scene['title']}': {unmatched}")

        enriched.append({
            "scene_id":     scene["scene_id"],
            "type":         scene["type"],
            "title":        scene["title"],
            "content":      scene["content"],
            "priority":     scene["priority"],
            "duration_hint": scene["duration_hint"],
            "elements":     matched,
            # Camera planning fields — populated later
            "camera": None,
        })

    return enriched


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     import json

#     mock_unified = {
#         "meta": {"url": "https://sumit.dev", "viewport": {"width": 1280, "height": 720}},
#         "elements": [
#             {"id": "el_001", "tag": "h1",     "text": "Sumit",         "bbox": {"x": 483, "y": 219, "width": 667, "height": 78}},
#             {"id": "el_002", "tag": "h3",     "text": "Hello, I'm",    "bbox": {"x": 483, "y": 163, "width": 667, "height": 56}},
#             {"id": "el_003", "tag": "button", "text": "View Projects", "bbox": {"x": 695, "y": 595, "width": 146, "height": 40}},
#             {"id": "el_004", "tag": "link",   "text": "Live Demo",     "bbox": {"x": 113, "y": 3884, "width": 56, "height": 56}},
#             {"id": "el_005", "tag": "link",   "text": "Live Demo",     "bbox": {"x": 113, "y": 4476, "width": 56, "height": 56}},
#         ]
#     }

#     mock_scenes = {
#         "scenes": [
#             {
#                 "scene_id": 1,
#                 "type": "introduction_hero",
#                 "title": "Meet Sumit",
#                 "content": "Hi, I'm Sumit, an AI Developer.",
#                 "priority": 10,
#                 "duration_hint": 5,
#                 "elements": ["H1: Sumit", "H3: Hello, I'm", "BUTTON: View Projects"],
#             }
#         ],
#         "skipped_noise": []
#     }

#     result = attach_coordinates(mock_scenes, mock_unified)
#     print(json.dumps(result, indent=2))