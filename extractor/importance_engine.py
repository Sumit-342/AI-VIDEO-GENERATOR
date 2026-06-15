import os
import json
import time
import logging
from google import genai
from dotenv import load_dotenv
from prompts import IMPORTANCE_RANKING_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Heuristic Pre-Scorer
# ---------------------------------------------------------------------------

# Universal signals based on HTML semantics — not website-specific
IMPORTANCE_SIGNALS = {
    "h1": 10,
    "h2": 6,
    "h3": 3,
    "button": 5,
}

# Keyword boosters — purpose-agnostic, works on any site
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
    "noise":   (NOISE_KEYWORDS,  -20),  # hard penalize noise
}


def _score_element(text: str, tag: str) -> int:
    """Score a single element using tag type + keyword signals."""
    score = IMPORTANCE_SIGNALS.get(tag, 2)
    text_lower = text.lower()

    for category, (keywords, boost) in KEYWORD_BOOST.items():
        if any(kw in text_lower for kw in keywords):
            score += boost
            break  # only apply one boost per element

    return max(score, 0)  # never negative


def heuristic_pre_score(clean_data: dict) -> list[dict]:
    """
    Score all website elements locally — no API needed.
    Returns top 15 elements sorted by score descending.
    """
    scored = []

    # Score headings
    for tag in ("h1", "h2", "h3"):
        for text in clean_data.get("heading", {}).get(tag, []):
            scored.append({
                "text": text,
                "tag": tag,
                "score": _score_element(text, tag),
            })

    # Score buttons
    for text in clean_data.get("buttons", []):
        scored.append({
            "text": text,
            "tag": "button",
            "score": _score_element(text, "button"),
        })

    # Score link texts (url not needed for importance)
    for link in clean_data.get("links", []):
        text = link.get("text", "")
        if text:
            scored.append({
                "text": text,
                "tag": "link",
                "score": _score_element(text, "link"),
            })

    # Sort by score, keep top 15 to minimize LLM tokens
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = [item for item in scored[:15] if item["score"] > 0]

    logger.info(f"Pre-scorer: {len(scored)} elements → top {len(top)} sent to LLM")
    return top

# ---------------------------------------------------------------------------
# LLM Importance Ranker
# ---------------------------------------------------------------------------

def _build_elements_text(scored_elements: list[dict]) -> str:
    """Format scored elements as compact text for LLM prompt."""
    lines = []
    for item in scored_elements:
        lines.append(f"[{item['tag'].upper()}] (score:{item['score']}) {item['text']}")
    return "\n".join(lines)


def _parse_response(text: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _validate_scenes(data: dict) -> dict:
    """Ensure scene output is well-formed with sane defaults."""
    # Accept any type LLM invents — only noise is special
    valid_types = None  # dynamic — no whitelist
    scenes = data.get("scenes", [])
    cleaned = []

    for i, scene in enumerate(scenes):
        scene_type = scene.get("type", "other").lower()
        # No whitelist — LLM invents meaningful types dynamically
        if not scene_type:
            scene_type = "other"

        cleaned.append({
            "scene_id":     i + 1,
            "type":         scene_type,
            "title":        scene.get("title", f"Scene {i+1}"),
            "content":      scene.get("content", ""),
            "elements":     scene.get("elements", []),
            "priority":     min(max(int(scene.get("priority", 5)), 1), 10),
            "duration_hint": min(max(int(scene.get("duration_hint", 4)), 3), 8),
        })

    # Sort by priority descending — video plays in this order
    cleaned.sort(key=lambda x: x["priority"], reverse=True)

    # Remove noise scenes — they don't appear in video
    video_scenes = [s for s in cleaned if s["type"] != "noise"]
    noise_scenes = [s for s in cleaned if s["type"] == "noise"]

    logger.info(f"Scenes: {len(video_scenes)} video + {len(noise_scenes)} noise (skipped)")
    return {"scenes": video_scenes, "skipped_noise": noise_scenes}

# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def rank_importance(clean_data: dict, purpose_data: dict, retries: int = 3) -> dict:
    """
    Rank website elements into video scenes using heuristics + LLM.

    Args:
        clean_data:   Output from clean_website_data()
        purpose_data: Output from detect_purpose()
        retries:      Retry attempts on LLM failure

    Returns:
        {scenes: [...], skipped_noise: [...]}
    """
    # Step 1 — free local pre-scoring
    scored_elements = heuristic_pre_score(clean_data)

    if not scored_elements:
        logger.warning("No scoreable elements found — returning empty scenes")
        return {"scenes": [], "skipped_noise": []}

    # Step 2 — build compact prompt
    elements_text = _build_elements_text(scored_elements)
    purpose = purpose_data.get("purpose", "other")
    prompt = IMPORTANCE_RANKING_PROMPT.format(
        purpose=purpose,
        primary_goal=purpose_data.get("primary_goal", "unknown"),
        elements=elements_text,
    )

    logger.info(f"Sending {len(scored_elements)} elements to LLM (~{len(prompt.split())} words)")

    # Step 3 — LLM call with retries
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Importance ranking attempt {attempt}...")

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )

            parsed = _parse_response(response.text)
            validated = _validate_scenes(parsed)
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

# if __name__ == "__main__":
#     from cleaner import clean_website_data
#     from purpose_detector import detect_purpose

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