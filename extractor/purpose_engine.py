import os
import json
import time
import logging
from google import genai
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv
from prompts import PURPOSE_DETECTION_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

# deepseek
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-pro"

#groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.3-70b-versatile"

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


def call_gemini(prompt):
    return client.models.generate_content(
        model=MODEL,
        contents=prompt
    ).text


def call_deepseek(prompt):
    res = deepseek_client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content



def call_groq(prompt):
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def detect_purpose(clean_data: dict, retries: int = 5) -> dict:
    prompt = _build_prompt(clean_data)

    providers = [
        ("gemini", call_gemini),
        ("deepseek", call_deepseek),
        ("groq", call_groq),
    ]

    last_error = None

    for name, provider in providers:
        logger.info(f"\n🚀 Switching to provider: {name}")

        for attempt in range(1, retries + 1):
            try:
                logger.info(f"🟡 {name} attempt {attempt}")

                raw = provider(prompt)

                parsed = _parse_response(raw)

                validated = _validate_purpose(parsed)

                # 🔥 DEBUG INFO (IMPORTANT FOR YOU)
                validated["provider_used"] = name

                logger.info(f"✅ SUCCESS from {name}")
                return validated

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"❌ JSON error in {name}: {e}")

            except Exception as e:
                last_error = e
                logger.warning(f"❌ API error in {name}: {e}")

            time.sleep(2 ** attempt)

    logger.error(f"❌ ALL PROVIDERS FAILED: {last_error}")

    return {
        "purpose": "other",
        "primary_goal": "unknown",
        "owner": None,
        "industry": None,
        "provider_used": "fallback"
    }


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_clean_data = {
        "title": "Sumit | Full Stack Developer",
        "heading": {
            "h1": ["Hi, I'm Sumit", "I Build Things for the Web"],
            "h2": ["About Me", "Projects", "Skills", "Contact"],
            "h3": ["Resume Analyzer", "Portfolio Website", "AI Video Generator"],
        },
        "buttons": ["View Projects", "Download CV", "Hire Me"],
        "links": [
            {"text": "GitHub", "url": "https://github.com/sumit"},
            {"text": "LinkedIn", "url": "https://linkedin.com/in/sumit"},
        ],
    }

    result = detect_purpose(sample_clean_data)
    print(json.dumps(result, indent=2))