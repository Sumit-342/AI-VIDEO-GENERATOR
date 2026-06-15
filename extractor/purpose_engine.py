import os
import json
import time
import logging
from google import genai
from dotenv import load_dotenv
from prompts import PURPOSE_DETECTION_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(clean_data: dict) -> str:
    return PURPOSE_DETECTION_PROMPT.format(
        title=clean_data.get("title", ""),
        h1=clean_data.get("heading", {}).get("h1", []),
        h2=clean_data.get("heading", {}).get("h2", []),
    )


def _parse_response(text: str) -> dict:
    """Safely parse LLM response — strips markdown fences if present."""
    text = text.strip()
    # Strip ```json or ``` fences if model adds them
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    return json.loads(text)


def _validate_purpose(data: dict) -> dict:
    """Ensure output has all required keys with sane defaults."""
    valid_purposes = {"portfolio", "saas", "ecommerce", "blog", "docs", "other"}
    purpose = data.get("purpose", "other").lower()
    if purpose not in valid_purposes:
        purpose = "other"

    return {
        "purpose": purpose,
        "primary_goal": data.get("primary_goal", "unknown"),
        "owner": data.get("owner", None),
        "industry": data.get("industry", None),
    }

# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def detect_purpose(clean_data: dict, retries: int = 3) -> dict:
    """
    Detect the purpose of a website from cleaned structured data.

    Args:
        clean_data: Output from clean_website_data()
        retries: Number of retry attempts on failure

    Returns:
        {purpose, primary_goal, owner, industry}
    """
    prompt = _build_prompt(clean_data)

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Purpose detection attempt {attempt}...")

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )

            parsed = _parse_response(response.text)
            validated = _validate_purpose(parsed)

            logger.info(f"Detected purpose: {validated['purpose']}")
            return validated

        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt} — JSON parse failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff

        except Exception as e:
            logger.error(f"Attempt {attempt} — API error: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

    # Fallback if all retries fail
    logger.error("All attempts failed — returning fallback purpose")
    return {
        "purpose": "other",
        "primary_goal": "unknown",
        "owner": None,
        "industry": None,
    }


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     sample_clean_data = {
#         "title": "Sumit | Full Stack Developer",
#         "heading": {
#             "h1": ["Hi, I'm Sumit", "I Build Things for the Web"],
#             "h2": ["About Me", "Projects", "Skills", "Contact"],
#             "h3": ["Resume Analyzer", "Portfolio Website", "AI Video Generator"],
#         },
#         "buttons": ["View Projects", "Download CV", "Hire Me"],
#         "links": [
#             {"text": "GitHub", "url": "https://github.com/sumit"},
#             {"text": "LinkedIn", "url": "https://linkedin.com/in/sumit"},
#         ],
#     }

#     result = detect_purpose(sample_clean_data)
#     print(json.dumps(result, indent=2))