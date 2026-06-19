# """
# Camera Engine — AI-powered camera director using Groq.
# Converts enriched scenes (with bbox + center) into cinematic camera instructions.
# """

# import os
# import json
# import time
# import logging
# from groq import Groq
# from dotenv import load_dotenv
# from prompts import CAMERA_DIRECTOR_SYSTEM_PROMPT, CAMERA_DIRECTOR_USER_PROMPT

# load_dotenv()
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# MODEL  = "llama-3.3-70b-versatile"

# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# TAG_PRIORITY = {"button": 10, "h1": 8, "h2": 6, "h3": 4, "link": 2}


# def _format_elements(elements: list[dict]) -> str:
#     """Compact element representation — minimizes tokens."""
#     lines = []
#     for el in elements:
#         c = el.get("center", {})
#         b = el.get("bbox", {})
#         lines.append(
#             f"[{el['tag'].upper()}] \"{el['text']}\" "
#             f"center=({round(c.get('x',0))},{round(c.get('y',0))}) "
#             f"size={round(b.get('width',0))}x{round(b.get('height',0))}"
#         )
#     return "\n".join(lines) if lines else "no elements"


# def _heuristic_fallback(scene: dict, scene_index: int, total: int) -> dict:
#     """
#     Pure heuristic camera plan — used when Groq fails.
#     Mirrors system prompt logic so fallback is consistent.
#     """
#     elements   = scene.get("elements", [])
#     scene_type = scene.get("type", "").lower()
#     duration   = scene.get("duration_hint", 5)

#     # Focus element — highest priority tag
#     focus_el = max(
#         (el for el in elements if el.get("center")),
#         key=lambda e: TAG_PRIORITY.get(e.get("tag", ""), 0),
#         default=None,
#     )
#     focus_point = focus_el["center"] if focus_el else {"x": 640, "y": 360}
#     focus_text  = focus_el["text"]   if focus_el else ""

#     # Zoom
#     if scene_index == 0:
#         zoom = 1.15
#     elif any(k in scene_type for k in ("cta", "contact")):
#         zoom = 1.5
#     elif any(k in scene_type for k in ("hero", "intro")):
#         zoom = 1.3
#     else:
#         zoom = 1.1

#     # Movement
#     ys = [el["center"]["y"] for el in elements if el.get("center")]
#     xs = [el["center"]["x"] for el in elements if el.get("center")]
#     y_spread = (max(ys) - min(ys)) if len(ys) > 1 else 0
#     x_spread = (max(xs) - min(xs)) if len(xs) > 1 else 0

#     if scene_index == 0 or any(k in scene_type for k in ("hero", "intro", "cta")):
#         movement = "zoom_in"
#     elif y_spread > 200:
#         movement = "scroll_down"
#     elif x_spread > 300:
#         movement = "pan_horizontal"
#     else:
#         movement = "zoom_in" if len(elements) == 1 else "static"

#     # Camera bias
#     x = focus_point.get("x", 640)
#     bias = "left" if x < 400 else ("right" if x > 880 else "center")

#     # Speed
#     speed = "fast" if duration <= 3 else ("medium" if duration <= 5 else "slow")

#     # Ease
#     ease_map = {"zoom_in": "ease_in_out", "scroll_down": "ease_in",
#                 "pan_horizontal": "ease_in_out", "static": "none"}
#     ease = ease_map.get(movement, "ease_in_out")

#     # Strength
#     strength = "subtle" if zoom <= 1.2 else ("moderate" if zoom <= 1.5 else "strong")

#     # Transition
#     if scene_index == 0:
#         transition = "fade"
#     elif movement == "scroll_down":
#         transition = "smooth_scroll"
#     else:
#         transition = "fade"

#     return {
#         "movement":            movement,
#         "zoom_level":          zoom,
#         "target_element_text": focus_text,
#         "focus_point":         focus_point,
#         "camera_bias":         bias,
#         "scroll_intent":       "down" if movement == "scroll_down" else "none",
#         "movement_speed":      speed,
#         "ease":                ease,
#         "motion_strength":     strength,
#         "transition_in":       transition,
#         "duration_factor":     1.0,
#         "confidence":          0.6,
#         "focus_reason":        "heuristic fallback",
#         "source":              "fallback",
#     }


# def _parse_groq_response(text: str) -> dict:
#     text = text.strip()
#     if text.startswith("```"):
#         text = text.split("```")[1]
#         if text.startswith("json"):
#             text = text[4:]
#     return json.loads(text.strip())


# def _validate_camera(data: dict) -> dict:
#     valid_movements  = {"zoom_in", "scroll_down", "pan_horizontal", "static"}
#     valid_biases     = {"left", "right", "center"}
#     valid_speeds     = {"slow", "medium", "fast"}
#     valid_eases      = {"ease_in", "ease_out", "ease_in_out", "none"}
#     valid_strengths  = {"subtle", "moderate", "strong"}
#     valid_transitions= {"fade", "smooth_scroll", "cut", "zoom_fade"}

#     return {
#         "movement":            data.get("movement",            "static")       if data.get("movement")            in valid_movements   else "static",
#         "zoom_level":          max(1.0, min(2.0, float(data.get("zoom_level", 1.1)))),
#         "target_element_text": data.get("target_element_text", ""),
#         "focus_point":         data.get("focus_point",         {"x": 640, "y": 360}),
#         "camera_bias":         data.get("camera_bias",         "center")       if data.get("camera_bias")         in valid_biases      else "center",
#         "scroll_intent":       data.get("scroll_intent",       "none"),
#         "movement_speed":      data.get("movement_speed",      "medium")       if data.get("movement_speed")      in valid_speeds      else "medium",
#         "ease":                data.get("ease",                "ease_in_out")  if data.get("ease")                in valid_eases       else "ease_in_out",
#         "motion_strength":     data.get("motion_strength",     "moderate")     if data.get("motion_strength")     in valid_strengths   else "moderate",
#         "transition_in":       data.get("transition_in",       "fade")         if data.get("transition_in")       in valid_transitions else "fade",
#         "duration_factor":     max(0.5, min(2.0, float(data.get("duration_factor", 1.0)))),
#         "confidence":          max(0.0, min(1.0, float(data.get("confidence", 0.8)))),
#         "focus_reason":        data.get("focus_reason",        "")[:120],
#         "source":              "groq",
#     }

# # ---------------------------------------------------------------------------
# # Per-scene Groq call
# # ---------------------------------------------------------------------------

# def _direct_scene(
#     scene: dict,
#     scene_index: int,
#     total: int,
#     retries: int = 2,
   
# ) -> dict:
#     elements = scene.get("elements", [])
#     prompt = CAMERA_DIRECTOR_USER_PROMPT.format(
#         scene_id=scene.get("scene_id", scene_index + 1),
#         scene_index=scene_index,
#         total_scenes=total,
#         scene_type=scene.get("type", "other"),
#         duration_hint=scene.get("duration_hint", 5),
#         elements_text=_format_elements(elements),
#         total_elements=len(elements),
#     )

#     for attempt in range(1, retries + 1):
#         try:
#             response = client.chat.completions.create(
#                 model    = MODEL,
#                 messages = [
#                     {"role": "system", "content": CAMERA_DIRECTOR_SYSTEM_PROMPT},
#                     {"role": "user",   "content": prompt},
#                 ],
#                 temperature = 0.2,   # low temp = consistent JSON
#                 max_tokens  = 256,   # camera block is small
#             )
#             raw     = response.choices[0].message.content
#             parsed  = _parse_groq_response(raw)
#             return _validate_camera(parsed)

#         except json.JSONDecodeError as e:
#             logger.warning(f"Scene {scene_index+1} attempt {attempt} — JSON error: {e}")
#             if attempt < retries:
#                 time.sleep(2 ** attempt)

#         except Exception as e:
#             logger.error(f"Scene {scene_index+1} attempt {attempt} — API error: {e}")
#             if attempt < retries:
#                 time.sleep(2 ** attempt)

#     logger.warning(f"Scene {scene_index+1} — Groq failed, using heuristic fallback")
#     return _heuristic_fallback(scene, scene_index, total)


# # ---------------------------------------------------------------------------
# # Main function
# # ---------------------------------------------------------------------------



# def generate_camera_plan(enriched_scenes: list[dict]) -> list[dict]:
#     """
#     Generate AI camera directions for each scene.

#     Args:
#         enriched_scenes: Output of attach_coordinates()

#     Returns:
#         Same scenes with "camera" block populated.
#     """
#     total  = len(enriched_scenes)
#     result = []

#     for i, scene in enumerate(enriched_scenes):
#         logger.info(f"Directing scene {i+1}/{total}: {scene.get('type')}")
#         camera = _direct_scene(scene, i, total)
#         result.append({**scene, "camera": camera})

    

#     return result


# # ---------------------------------------------------------------------------
# # Quick test (no API — uses fallback)
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     mock_scenes = [
#         {
#             "scene_id": 1, "type": "introduction_hero", "duration_hint": 5, "camera": None,
#             "elements": [
#                 {"text": "Sumit",         "tag": "h1",     "bbox": {"x": 483, "y": 219, "width": 667, "height": 78},  "center": {"x": 816.5, "y": 258.0}},
#                 {"text": "View Projects", "tag": "button", "bbox": {"x": 695, "y": 595, "width": 146, "height": 40},  "center": {"x": 768.0, "y": 615.0}},
#             ],
#         },
#         {
#             "scene_id": 2, "type": "skills_overview", "duration_hint": 6, "camera": None,
#             "elements": [
#                 {"text": "My Skills",        "tag": "h1", "bbox": {"x": 0,   "y": 1440, "width": 1264, "height": 190}, "center": {"x": 632.0, "y": 1535.0}},
#                 {"text": "Technical Skills", "tag": "h3", "bbox": {"x": 352, "y": 1750, "width": 560,  "height": 57},  "center": {"x": 632.0, "y": 1778.5}},
#                 {"text": "Soft Skills",      "tag": "h2", "bbox": {"x": 367, "y": 2413, "width": 560,  "height": 57},  "center": {"x": 647.0, "y": 2441.5}},
#             ],
#         },
#         {
#             "scene_id": 3, "type": "contact_call_to_action", "duration_hint": 4, "camera": None,
#             "elements": [
#                 {"text": "Let's Connect", "tag": "button", "bbox": {"x": 622, "y": 5207, "width": 550, "height": 47}, "center": {"x": 897.0, "y": 5230.5}},
#             ],
#         },
#     ]

#     final = generate_camera_plan(mock_scenes)
#     print(json.dumps(final, indent=2))
















"""
Camera Engine — AI-powered camera director using Groq.
Converts enriched scenes (with bbox + center) into cinematic camera instructions.
"""

import os
import json
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from prompts import CAMERA_DIRECTOR_SYSTEM_PROMPT, CAMERA_DIRECTOR_USER_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TAG_PRIORITY = {"button": 10, "h1": 8, "h2": 6, "h3": 4, "link": 2}


def _format_elements(elements: list[dict]) -> str:
    """Compact element representation — minimizes tokens."""
    lines = []
    for el in elements:
        c = el.get("center", {})
        b = el.get("bbox", {})
        lines.append(
            f"[{el['tag'].upper()}] \"{el['text']}\" "
            f"center=({round(c.get('x',0))},{round(c.get('y',0))}) "
            f"size={round(b.get('width',0))}x{round(b.get('height',0))}"
        )
    return "\n".join(lines) if lines else "no elements"


def _heuristic_fallback(scene: dict, scene_index: int, total: int) -> dict:
    """
    Pure heuristic camera plan — used when Groq fails.
    Mirrors system prompt logic so fallback is consistent.
    """
    elements   = scene.get("elements", [])
    scene_type = scene.get("type", "").lower()
    duration   = scene.get("duration_hint", 5)

    # Focus element — highest priority tag
    focus_el = max(
        (el for el in elements if el.get("center")),
        key=lambda e: TAG_PRIORITY.get(e.get("tag", ""), 0),
        default=None,
    )
    focus_point = focus_el["center"] if focus_el else {"x": 640, "y": 360}
    focus_text  = focus_el["text"]   if focus_el else ""

    # Zoom
    if scene_index == 0:
        zoom = 1.15
    elif any(k in scene_type for k in ("cta", "contact")):
        zoom = 1.5
    elif any(k in scene_type for k in ("hero", "intro")):
        zoom = 1.3
    else:
        zoom = 1.1

    # Movement
    ys = [el["center"]["y"] for el in elements if el.get("center")]
    xs = [el["center"]["x"] for el in elements if el.get("center")]
    y_spread = (max(ys) - min(ys)) if len(ys) > 1 else 0
    x_spread = (max(xs) - min(xs)) if len(xs) > 1 else 0

    if scene_index == 0 or any(k in scene_type for k in ("hero", "intro", "cta")):
        movement = "zoom_in"
    elif y_spread > 200:
        movement = "scroll_down"
    elif x_spread > 300:
        movement = "pan_horizontal"
    else:
        movement = "zoom_in" if len(elements) == 1 else "static"

    # Camera bias
    x = focus_point.get("x", 640)
    bias = "left" if x < 400 else ("right" if x > 880 else "center")

    # Speed
    speed = "fast" if duration <= 3 else ("medium" if duration <= 5 else "slow")

    # Ease
    ease_map = {"zoom_in": "ease_in_out", "scroll_down": "ease_in",
                "pan_horizontal": "ease_in_out", "static": "none"}
    ease = ease_map.get(movement, "ease_in_out")

    # Strength
    strength = "subtle" if zoom <= 1.2 else ("moderate" if zoom <= 1.5 else "strong")

    # Transition
    if scene_index == 0:
        transition = "fade"
    elif movement == "scroll_down":
        transition = "smooth_scroll"
    else:
        transition = "fade"

    return {
        "movement":            movement,
        "zoom_level":          zoom,
        "target_element_text": focus_text,
        "focus_point":         focus_point,
        "camera_bias":         bias,
        "scroll_intent":       "down" if movement == "scroll_down" else "none",
        "movement_speed":      speed,
        "ease":                ease,
        "motion_strength":     strength,
        "transition_in":       transition,
        "duration_factor":     1.0,
        "confidence":          0.6,
        "focus_reason":        "heuristic fallback",
        "source":              "fallback",
    }


def _parse_groq_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _validate_camera(data: dict) -> dict:
    valid_movements  = {"zoom_in", "scroll_down", "pan_horizontal", "static"}
    valid_biases     = {"left", "right", "center"}
    valid_speeds     = {"slow", "medium", "fast"}
    valid_eases      = {"ease_in", "ease_out", "ease_in_out", "none"}
    valid_strengths  = {"subtle", "moderate", "strong"}
    valid_transitions= {"fade", "smooth_scroll", "cut", "zoom_fade"}

    return {
        "movement":            data.get("movement",            "static")       if data.get("movement")            in valid_movements   else "static",
        "zoom_level":          max(1.0, min(2.0, float(data.get("zoom_level", 1.1)))),
        "target_element_text": data.get("target_element_text", ""),
        "focus_point":         data.get("focus_point",         {"x": 640, "y": 360}),
        "camera_bias":         data.get("camera_bias",         "center")       if data.get("camera_bias")         in valid_biases      else "center",
        "scroll_intent":       data.get("scroll_intent",       "none"),
        "movement_speed":      data.get("movement_speed",      "medium")       if data.get("movement_speed")      in valid_speeds      else "medium",
        "ease":                data.get("ease",                "ease_in_out")  if data.get("ease")                in valid_eases       else "ease_in_out",
        "motion_strength":     data.get("motion_strength",     "moderate")     if data.get("motion_strength")     in valid_strengths   else "moderate",
        "transition_in":       data.get("transition_in",       "fade")         if data.get("transition_in")       in valid_transitions else "fade",
        "duration_factor":     max(0.5, min(2.0, float(data.get("duration_factor", 1.0)))),
        "confidence":          max(0.0, min(1.0, float(data.get("confidence", 0.8)))),
        "focus_reason":        data.get("focus_reason",        "")[:120],
        "source":              "groq",
    }

# ---------------------------------------------------------------------------
# Per-scene Groq call
# ---------------------------------------------------------------------------

def _direct_scene(
    scene: dict,
    scene_index: int,
    total: int,
    retries: int = 2,
) -> dict:
    prompt = CAMERA_DIRECTOR_USER_PROMPT.format(
        scene_id     = scene.get("scene_id", scene_index + 1),
        scene_index  = scene_index,
        total_scenes = total,
        scene_type   = scene.get("type", "other"),
        duration_hint= scene.get("duration_hint", 5),
        elements_text= _format_elements(scene.get("elements", [])),
    )

    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model    = MODEL,
                messages = [
                    {"role": "system", "content": CAMERA_DIRECTOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature = 0.2,   # low temp = consistent JSON
                max_tokens  = 256,   # camera block is small
            )
            raw     = response.choices[0].message.content
            parsed  = _parse_groq_response(raw)
            return _validate_camera(parsed)

        except json.JSONDecodeError as e:
            logger.warning(f"Scene {scene_index+1} attempt {attempt} — JSON error: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Scene {scene_index+1} attempt {attempt} — API error: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

    logger.warning(f"Scene {scene_index+1} — Groq failed, using heuristic fallback")
    return _heuristic_fallback(scene, scene_index, total)


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def detect_backward_jumps(scenes: list[dict]) -> list[dict]:
    """
    Detects if a scene's average Y position is significantly LOWER
    (i.e. higher up the page) than the previous scene's Y. If so,
    marks that scene's camera transition as a hard 'cut' instead of
    'smooth_scroll' — avoiding a jarring reverse-scroll animation
    where the camera would otherwise scroll backward up the page.

    This is a pure rules-based safety net — it runs AFTER the LLM
    camera director, so it works regardless of what order the
    importance engine decided to put scenes in.
    """
    def primary_y(scene):
        """
        Use the position of the scene's FOCUS element (camera target),
        not a raw average — averaging breaks when one scene mixes a
        top-of-page element with a bottom-of-page element (e.g. intro
        scene also containing a CTA heading from the page footer),
        which artificially inflates/deflates the average and hides
        real backward jumps.
        """
        elements = scene.get("elements", [])
        if not elements:
            return 0
        target_text = scene.get("camera", {}).get("target_element_text", "")
        for el in elements:
            if el.get("text") == target_text:
                return el["bbox"]["y"]
        # Fallback — topmost element in the scene
        return min(el["bbox"]["y"] for el in elements)

    for i in range(1, len(scenes)):
        prev_y = primary_y(scenes[i - 1])
        curr_y = primary_y(scenes[i])

        if curr_y < prev_y - 300:  # significant backward jump
            scenes[i]["camera"]["transition_in"]  = "cut"
            scenes[i]["camera"]["movement"]       = "zoom_in"
            scenes[i]["camera"]["scroll_intent"]  = "none"
            logger.info(
                f"Scene {scenes[i].get('scene_id')}: backward jump detected "
                f"(prev_y={prev_y:.0f} → curr_y={curr_y:.0f}), forcing cut transition"
            )

    return scenes


def generate_camera_plan(enriched_scenes: list[dict]) -> list[dict]:
    """
    Generate AI camera directions for each scene.

    Args:
        enriched_scenes: Output of attach_coordinates()

    Returns:
        Same scenes with "camera" block populated.
    """
    total  = len(enriched_scenes)
    result = []

    for i, scene in enumerate(enriched_scenes):
        logger.info(f"Directing scene {i+1}/{total}: {scene.get('type')}")
        camera = _direct_scene(scene, i, total)
        result.append({**scene, "camera": camera})

    # Post-process: fix any backward (upward) scroll jumps between
    # consecutive scenes so playback never does a jarring reverse-scroll.
    result = detect_backward_jumps(result)

    return result


# ---------------------------------------------------------------------------
# Quick test (no API — uses fallback)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mock_scenes = [
        {
            "scene_id": 1, "type": "introduction_hero", "duration_hint": 5, "camera": None,
            "elements": [
                {"text": "Sumit",         "tag": "h1",     "bbox": {"x": 483, "y": 219, "width": 667, "height": 78},  "center": {"x": 816.5, "y": 258.0}},
                {"text": "View Projects", "tag": "button", "bbox": {"x": 695, "y": 595, "width": 146, "height": 40},  "center": {"x": 768.0, "y": 615.0}},
            ],
        },
        {
            "scene_id": 2, "type": "skills_overview", "duration_hint": 6, "camera": None,
            "elements": [
                {"text": "My Skills",        "tag": "h1", "bbox": {"x": 0,   "y": 1440, "width": 1264, "height": 190}, "center": {"x": 632.0, "y": 1535.0}},
                {"text": "Technical Skills", "tag": "h3", "bbox": {"x": 352, "y": 1750, "width": 560,  "height": 57},  "center": {"x": 632.0, "y": 1778.5}},
                {"text": "Soft Skills",      "tag": "h2", "bbox": {"x": 367, "y": 2413, "width": 560,  "height": 57},  "center": {"x": 647.0, "y": 2441.5}},
            ],
        },
        {
            "scene_id": 3, "type": "contact_call_to_action", "duration_hint": 4, "camera": None,
            "elements": [
                {"text": "Let's Connect", "tag": "button", "bbox": {"x": 622, "y": 5207, "width": 550, "height": 47}, "center": {"x": 897.0, "y": 5230.5}},
            ],
        },
    ]

    final = generate_camera_plan(mock_scenes)
    print(json.dumps(final, indent=2))