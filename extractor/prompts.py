PURPOSE_DETECTION_PROMPT = """
You are an expert website analyst.

Analyze the website data below and identify its purpose and goal.

WEBSITE DATA:
Title: {title}
H1 Headings: {h1}
H2 Headings: {h2}

INSTRUCTIONS:
- Return ONLY valid JSON, no explanation, no markdown, no backticks
- "purpose" must be exactly one of: portfolio, saas, ecommerce, blog, docs, other
- "primary_goal" must be max 10 words
- "owner" is the person/company name if found, else null
- "industry" is the domain like tech, finance, design, etc., else null

RETURN THIS EXACT FORMAT:
{{
  "purpose": "portfolio",
  "primary_goal": "showcase work and get hired",
  "owner": "Sumit",
  "industry": "tech"
}}
"""


IMPORTANCE_RANKING_PROMPT = """
You are an expert video scene planner for websites.

WEBSITE PURPOSE: {purpose}
PRIMARY GOAL: {primary_goal}

WEBSITE ELEMENTS (pre-scored by importance, higher score = more important):
{elements}

YOUR JOB:
Group these elements into logical video scenes that best represent THIS website.
Think like a human who watched this website and is now explaining it in a short video.

SCENE TYPE RULES:
- You MUST invent scene type names that make sense for THIS specific website
- Do NOT use generic types like "other" unless truly no better name fits
- Examples for a docs site: "introduction", "core_features", "security", "deployment", "community"
- Examples for a portfolio: "intro", "projects", "tech_stack", "contact"
- Examples for a saas: "value_proposition", "features", "pricing", "social_proof"
- "noise" type is special — use ONLY for nav links, footer, cookie, legal text (these get skipped in video)

STRICT INSTRUCTIONS:
- Return ONLY valid JSON, no explanation, no markdown, no backticks
- Max 6 scenes total (excluding noise)
- "content" = narration script, max 2 sentences, natural spoken English, present tense
- "priority" 10 = show first, 1 = show last
- "duration_hint" = seconds this scene plays (3 to 8)
- Every element must belong to exactly one scene
- Scene titles must be specific, not generic ("FastAPI Security" not just "Security")

RETURN THIS EXACT FORMAT:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "type": "your_invented_type_here",
      "title": "Specific Scene Title",
      "content": "Natural narration for this scene in spoken English.",
      "elements": ["element1", "element2"],
      "priority": 10,
      "duration_hint": 4
    }}
  ]
}}
"""