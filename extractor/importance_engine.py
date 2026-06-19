# import os
# import json
# import time
# import logging
# from google import genai
# from openai import OpenAI
# from groq import Groq
# from dotenv import load_dotenv
# from prompts import IMPORTANCE_RANKING_PROMPT

# load_dotenv()
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Client
# # ---------------------------------------------------------------------------

# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# MODEL = "gemini-2.5-flash-lite"


# # deepseek
# deepseek_client = OpenAI(
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url="https://integrate.api.nvidia.com/v1",
# )

# DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-pro"

# #groq
# groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# GROQ_MODEL = "llama-3.3-70b-versatile"


# def call_gemini(prompt):
#     return client.models.generate_content(
#         model=MODEL,
#         contents=prompt
#     ).text


# def call_deepseek(prompt):
#     res = deepseek_client.chat.completions.create(
#         model=DEEPSEEK_MODEL,
#         messages=[{"role": "user", "content": prompt}]
#     )
#     return res.choices[0].message.content



# def call_groq(prompt):
#     res = groq_client.chat.completions.create(
#         model=GROQ_MODEL,
#         messages=[{"role": "user", "content": prompt}]
#     )
#     return res.choices[0].message.content


# def run_with_fallback(prompt, retries=3):
#     providers = [
#         ("gemini", call_gemini),
#         ("deepseek", call_deepseek),
#         ("groq", call_groq),
#     ]

#     for name, provider in providers:
#         logger.info(f"🚀 Trying provider: {name}")

#         for attempt in range(1, retries + 1):
#             try:
#                 raw = provider(prompt)
#                 logger.info(f"✅ Success from {name}")
#                 return raw, name

#             except Exception as e:
#                 logger.warning(f"❌ {name} attempt {attempt} failed: {e}")

#                 time.sleep(2 ** attempt)

#     return None, "fallback"
# # ---------------------------------------------------------------------------
# # Heuristic Pre-Scorer
# # ---------------------------------------------------------------------------

# # Universal signals based on HTML semantics — not website-specific
# IMPORTANCE_SIGNALS = {
#     "h1": 10,
#     "h2": 6,
#     "h3": 3,
#     "button": 5,
# }

# # Keyword boosters — purpose-agnostic, works on any site
# CTA_KEYWORDS      = {"hire", "contact", "download", "buy", "get started", "sign up", "try", "book", "order", "subscribe"}
# HERO_KEYWORDS     = {"welcome", "i am", "i'm", "we are", "we're", "hello", "hi", "about us", "who we are"}
# PROJECT_KEYWORDS  = {"project", "work", "portfolio", "case study", "built", "developed", "created", "product", "feature"}
# SKILL_KEYWORDS    = {"skill", "technology", "tech stack", "tools", "expertise", "experience", "proficient"}
# NOISE_KEYWORDS    = {"cookie", "privacy", "terms", "footer", "copyright", "nav", "menu", "sitemap", "back to top"}

# KEYWORD_BOOST = {
#     "cta":     (CTA_KEYWORDS,     8),
#     "hero":    (HERO_KEYWORDS,    9),
#     "project": (PROJECT_KEYWORDS, 7),
#     "skill":   (SKILL_KEYWORDS,   5),
#     "noise":   (NOISE_KEYWORDS,  -20),  # hard penalize noise
# }


# def _score_element(text: str, tag: str) -> int:
#     """Score a single element using tag type + keyword signals."""
#     score = IMPORTANCE_SIGNALS.get(tag, 2)
#     text_lower = text.lower()

#     for category, (keywords, boost) in KEYWORD_BOOST.items():
#         if any(kw in text_lower for kw in keywords):
#             score += boost
#             break  # only apply one boost per element

#     return max(score, 0)  # never negative


# def heuristic_pre_score(clean_data: dict) -> list[dict]:
#     """
#     Score all website elements locally — no API needed.
#     Returns top 15 elements sorted by score descending.
#     """
#     scored = []

#     # Score headings
#     for tag in ("h1", "h2", "h3"):
#         for text in clean_data.get("heading", {}).get(tag, []):
#             scored.append({
#                 "text": text,
#                 "tag": tag,
#                 "score": _score_element(text, tag),
#             })

#     # Score buttons
#     for text in clean_data.get("buttons", []):
#         scored.append({
#             "text": text,
#             "tag": "button",
#             "score": _score_element(text, "button"),
#         })

#     # Score link texts (url not needed for importance)
#     for link in clean_data.get("links", []):
#         text = link.get("text", "")
#         if text:
#             scored.append({
#                 "text": text,
#                 "tag": "link",
#                 "score": _score_element(text, "link"),
#             })

#     # Sort by score, keep top 15 to minimize LLM tokens
#     scored.sort(key=lambda x: x["score"], reverse=True)
#     top = [item for item in scored[:15] if item["score"] > 0]

#     logger.info(f"Pre-scorer: {len(scored)} elements → top {len(top)} sent to LLM")
#     return top

# # ---------------------------------------------------------------------------
# # LLM Importance Ranker
# # ---------------------------------------------------------------------------

# def _build_elements_text(scored_elements: list[dict]) -> str:
#     """Format scored elements as compact text for LLM prompt."""
#     lines = []
#     for item in scored_elements:
#         lines.append(f"[{item['tag'].upper()}] (score:{item['score']}) {item['text']}")
#     return "\n".join(lines)


# def _parse_response(text: str) -> dict:
#     """Strip markdown fences and parse JSON safely."""
#     text = text.strip()
#     if text.startswith("```"):
#         text = text.split("```")[1]
#         if text.startswith("json"):
#             text = text[4:]
#     return json.loads(text.strip())


# def _validate_scenes(data: dict) -> dict:
#     """Ensure scene output is well-formed with sane defaults."""
#     # Accept any type LLM invents — only noise is special
#     valid_types = None  # dynamic — no whitelist
#     scenes = data.get("scenes", [])
#     cleaned = []

#     for i, scene in enumerate(scenes):
#         scene_type = scene.get("type", "other").lower()
#         # No whitelist — LLM invents meaningful types dynamically
#         if not scene_type:
#             scene_type = "other"

#         cleaned.append({
#             "scene_id":     i + 1,
#             "type":         scene_type,
#             "title":        scene.get("title", f"Scene {i+1}"),
#             "content":      scene.get("content", ""),
#             "elements":     scene.get("elements", []),
#             "priority":     min(max(int(scene.get("priority", 5)), 1), 10),
#             "duration_hint": min(max(int(scene.get("duration_hint", 4)), 3), 8),
#         })

#     # Sort by priority descending — video plays in this order
#     cleaned.sort(key=lambda x: x["priority"], reverse=True)

#     # Remove noise scenes — they don't appear in video
#     video_scenes = [s for s in cleaned if s["type"] != "noise"]
#     noise_scenes = [s for s in cleaned if s["type"] == "noise"]

#     logger.info(f"Scenes: {len(video_scenes)} video + {len(noise_scenes)} noise (skipped)")
#     return {"scenes": video_scenes, "skipped_noise": noise_scenes}

# # ---------------------------------------------------------------------------
# # Main function
# # ---------------------------------------------------------------------------

# def rank_importance(clean_data: dict, purpose_data: dict, retries: int = 3) -> dict:
#     """
#     Rank website elements into video scenes using heuristics + LLM.

#     Args:
#         clean_data:   Output from clean_website_data()
#         purpose_data: Output from detect_purpose()
#         retries:      Retry attempts on LLM failure

#     Returns:
#         {scenes: [...], skipped_noise: [...]}
#     """
#     # Step 1 — free local pre-scoring
#     scored_elements = heuristic_pre_score(clean_data)

#     if not scored_elements:
#         logger.warning("No scoreable elements found — returning empty scenes")
#         return {"scenes": [], "skipped_noise": []}

#     # Step 2 — build compact prompt
#     elements_text = _build_elements_text(scored_elements)
#     purpose = purpose_data.get("purpose", "other")
#     prompt = IMPORTANCE_RANKING_PROMPT.format(
#         purpose=purpose,
#         primary_goal=purpose_data.get("primary_goal", "unknown"),
#         elements=elements_text,
#     )

#     logger.info(f"Sending {len(scored_elements)} elements to LLM (~{len(prompt.split())} words)")

#     # Step 3 — LLM call with retries
#     for attempt in range(1, retries + 1):
#         try:
#             logger.info(f"Importance ranking attempt {attempt}...")

#             raw, provider_used = run_with_fallback(prompt, retries)
#             if not raw:
#                 logger.error("All providers failed")
#                 return {"scenes": [], "skipped_noise": []}

#             parsed = _parse_response(raw)
#             validated = _validate_scenes(parsed)

#             validated["provider_used"] = provider_used
#             return validated

#         except json.JSONDecodeError as e:
#             logger.warning(f"Attempt {attempt} — JSON parse failed: {e}")
#             if attempt < retries:
#                 time.sleep(2 ** attempt)

#         except Exception as e:
#             logger.error(f"Attempt {attempt} — API error: {e}")
#             if attempt < retries:
#                 time.sleep(2 ** attempt)

#     logger.error("All attempts failed — returning empty scenes")
#     return {"scenes": [], "skipped_noise": []}


# # ---------------------------------------------------------------------------
# # Quick test
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     from cleaner import clean_website_data
#     from purpose_engine import detect_purpose

#     raw_data = {
#         "title": "Sumit | Full Stack Developer",
#         "heading": {
#             "h1": ["Hi, I'm Sumit", "I Build Things for the Web"],
#             "h2": ["About Me", "My Projects", "Skills", "Contact Me"],
#             "h3": ["Resume Analyzer", "AI Video Generator", "Portfolio Website", "React", "Python", "Node.js"],
#         },
#         "buttons": ["View Projects", "Download CV", "Hire Me", "Contact Me"],
#         "links": [
#             {"text": "GitHub",   "url": "https://github.com/sumit"},
#             {"text": "LinkedIn", "url": "https://linkedin.com/in/sumit"},
#             {"text": "Privacy Policy", "url": "https://example.com/privacy"},
#         ],
#     }

#     clean   = clean_website_data(raw_data)
#     purpose = detect_purpose(clean)
#     result  = rank_importance(clean, purpose)

#     print(json.dumps(result, indent=2))








import os
import json
import time
import logging
from google import genai
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv
from prompts import IMPORTANCE_RANKING_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)
DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-pro"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.3-70b-versatile"


def call_gemini(prompt):
    return client.models.generate_content(model=MODEL, contents=prompt).text


def call_deepseek(prompt):
    res = deepseek_client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def call_groq(prompt):
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def run_with_fallback(prompt, retries=3):
    providers = [
        ("gemini", call_gemini),
        ("deepseek", call_deepseek),
        ("groq", call_groq),
    ]
    for name, provider in providers:
        logger.info(f"🚀 Trying provider: {name}")
        for attempt in range(1, retries + 1):
            try:
                raw = provider(prompt)
                logger.info(f"✅ Success from {name}")
                return raw, name
            except Exception as e:
                logger.warning(f"❌ {name} attempt {attempt} failed: {e}")
                time.sleep(2 ** attempt)
    return None, "fallback"


# ---------------------------------------------------------------------------
# Heuristic Pre-Scorer
# ---------------------------------------------------------------------------

IMPORTANCE_SIGNALS = {"h1": 10, "h2": 6, "h3": 3, "button": 5}

CTA_KEYWORDS      = {"hire", "contact", "download", "buy", "get started", "sign up", "try", "book", "order", "subscribe"}
HERO_KEYWORDS     = {"welcome", "i am", "i'm", "we are", "we're", "hello", "hi", "about us", "who we are"}
PROJECT_KEYWORDS  = {"project", "work", "portfolio", "case study", "built", "developed", "created", "product", "feature"}
SKILL_KEYWORDS    = {"skill", "technology", "tech stack", "tools", "expertise", "experience", "proficient"}
NOISE_KEYWORDS    = {"cookie", "privacy", "terms", "footer", "copyright", "nav", "menu", "sitemap", "back to top"}

KEYWORD_BOOST = {
    "cta":     (CTA_KEYWORDS,     8),
    "hero":    (HERO_KEYWORDS,    9),
    "project": (PROJECT_KEYWORDS, 7),
    "skill":   (SKILL_KEYWORDS,   5),
    "noise":   (NOISE_KEYWORDS,  -20),
}


def _score_element(text: str, tag: str) -> int:
    score = IMPORTANCE_SIGNALS.get(tag, 2)
    text_lower = text.lower()
    for category, (keywords, boost) in KEYWORD_BOOST.items():
        if any(kw in text_lower for kw in keywords):
            score += boost
            break
    return max(score, 0)


def heuristic_pre_score(unified: dict) -> list[dict]:
    """
    Score all website elements locally — no API needed.

    IMPORTANT CHANGE: takes the UNIFIED extractor output (with real
    el_xxxxx ids) instead of the legacy clean_data dict. This is what
    lets us pass real, stable IDs through to the LLM — the previous
    version only had raw text, which is why the LLM had nothing to
    anchor its output to and started hallucinating ids like "el_8",
    "el_16", "el_17" that never existed anywhere in the pipeline.

    Returns top 15 elements sorted by score descending, each carrying
    its original "id" field straight from the extractor.
    """
    scored = []
    seen_text_tag = set()

    for el in unified.get("elements", []):
        tag  = el.get("tag", "")
        text = el.get("text", "")
        if tag not in ("h1", "h2", "h3", "button", "link"):
            continue

        # Dedup identical (tag, text) pairs — common with repeated nav
        # links (e.g. "Contact" appearing in both desktop + mobile nav,
        # or a button that also has a wrapping <a> link with the same
        # label). Keep the FIRST occurrence only — it's already sorted
        # top-to-bottom by the extractor, so first = highest on page.
        dedup_key = (tag, text.lower().strip())
        if dedup_key in seen_text_tag:
            continue
        seen_text_tag.add(dedup_key)

        scored.append({
            "id":    el["id"],          # <-- real id, carried through, never regenerated
            "text":  text,
            "tag":   tag,
            "score": _score_element(text, tag),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = [item for item in scored[:15] if item["score"] > 0]

    logger.info(f"Pre-scorer: {len(scored)} elements → top {len(top)} sent to LLM")
    return top


# ---------------------------------------------------------------------------
# LLM Importance Ranker
# ---------------------------------------------------------------------------

def _build_elements_text(scored_elements: list[dict]) -> str:
    """Format scored elements with their real id visible to the LLM."""
    lines = []
    for item in scored_elements:
        lines.append(f"[{item['id']}] ({item['tag'].upper()}, score:{item['score']}) {item['text']}")
    return "\n".join(lines)


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _validate_scenes(data: dict, valid_ids: set[str]) -> dict:
    """
    Ensure scene output is well-formed AND strips any hallucinated ids.

    KEY FIX: any id in a scene's "elements" array that is NOT in
    valid_ids (the exact set sent to the LLM) is dropped here — this
    is the strict string match the pipeline needs. No fuzzy text
    matching, no silent empty-array failures downstream.
    """
    scenes = data.get("scenes", [])
    cleaned = []
    seen_ids: set[str] = set()

    for i, scene in enumerate(scenes):
        scene_type = (scene.get("type") or "other").lower()

        raw_ids = scene.get("elements", [])
        kept_ids = []
        for eid in raw_ids:
            eid = str(eid).strip()
            if eid in valid_ids and eid not in seen_ids:
                kept_ids.append(eid)
                seen_ids.add(eid)
            elif eid not in valid_ids:
                logger.warning(f"Dropping hallucinated id '{eid}' from scene '{scene.get('title')}'")

        cleaned.append({
            "scene_id":      i + 1,
            "type":          scene_type,
            "title":         scene.get("title", f"Scene {i+1}"),
            "content":       scene.get("content", ""),
            "elements":      kept_ids,          # <-- now a list of REAL ids only
            "priority":      min(max(int(scene.get("priority", 5)), 1), 10),
            "duration_hint": min(max(int(scene.get("duration_hint", 4)), 3), 8),
        })

    # Any valid id the LLM forgot to place anywhere — append to the
    # lowest-priority non-noise scene rather than losing it silently.
    missing = valid_ids - seen_ids
    if missing and cleaned:
        fallback_scene = min(
            (s for s in cleaned if s["type"] != "noise"),
            key=lambda s: s["priority"],
            default=cleaned[0],
        )
        fallback_scene["elements"].extend(sorted(missing))
        logger.warning(f"{len(missing)} unplaced ids appended to '{fallback_scene['title']}'")

    # Sort by priority descending — video plays in this order
    cleaned.sort(key=lambda x: x["priority"], reverse=True)

    # Re-number scene_id sequentially AFTER sort, so downstream code
    # (camera_engine, scene_builder) always sees scene_id matching
    # actual array position — eliminates the "scene 5 before scene 4"
    # ordering bug.
    for idx, s in enumerate(cleaned):
        s["scene_id"] = idx + 1

    video_scenes = [s for s in cleaned if s["type"] != "noise"]
    noise_scenes = [s for s in cleaned if s["type"] == "noise"]

    logger.info(f"Scenes: {len(video_scenes)} video + {len(noise_scenes)} noise (skipped)")
    return {"scenes": video_scenes, "skipped_noise": noise_scenes}


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def rank_importance(unified: dict, purpose_data: dict, retries: int = 3) -> dict:
    """
    Rank website elements into video scenes using heuristics + LLM.

    Args:
        unified:      Output from extract_website() — the UNIFIED dict
                       with real element ids (NOT the legacy dict).
        purpose_data:  Output from detect_purpose()
        retries:       Retry attempts on LLM failure

    Returns:
        {scenes: [...], skipped_noise: [...]}
    """
    scored_elements = heuristic_pre_score(unified)

    if not scored_elements:
        logger.warning("No scoreable elements found — returning empty scenes")
        return {"scenes": [], "skipped_noise": []}

    valid_ids = {item["id"] for item in scored_elements}

    elements_text = _build_elements_text(scored_elements)
    purpose = purpose_data.get("purpose", "other")
    prompt = IMPORTANCE_RANKING_PROMPT.format(
        purpose=purpose,
        primary_goal=purpose_data.get("primary_goal", "unknown"),
        elements=elements_text,
        valid_ids=", ".join(sorted(valid_ids)),
    )

    logger.info(f"Sending {len(scored_elements)} elements to LLM (~{len(prompt.split())} words)")

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Importance ranking attempt {attempt}...")

            raw, provider_used = run_with_fallback(prompt, retries)
            if not raw:
                logger.error("All providers failed")
                return {"scenes": [], "skipped_noise": []}

            parsed = _parse_response(raw)
            validated = _validate_scenes(parsed, valid_ids)
            validated["provider_used"] = provider_used
            return validated

        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt} — JSON parse failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Attempt {attempt} — API error: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

    logger.error("All attempts failed — returning empty scenes")
    return {"scenes": [], "skipped_noise": []}


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from purpose_engine import detect_purpose
    from cleaner import clean_website_data

    mock_unified = {
        "elements": [
            {"id": "el_001", "tag": "h1",     "text": "Hi, I'm Sumit"},
            {"id": "el_002", "tag": "h2",     "text": "Projects"},
            {"id": "el_003", "tag": "button", "text": "Hire Me"},
            {"id": "el_004", "tag": "h3",     "text": "Resume Analyzer"},
        ]
    }

    legacy_for_purpose = {
        "title": "Sumit | Developer",
        "heading": {"h1": ["Hi, I'm Sumit"], "h2": ["Projects"], "h3": []},
    }

    clean = clean_website_data(legacy_for_purpose)
    purpose = detect_purpose(clean)
    result = rank_importance(mock_unified, purpose)

    print(json.dumps(result, indent=2))