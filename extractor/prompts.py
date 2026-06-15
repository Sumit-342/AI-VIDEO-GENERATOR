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
You are a video scene planner for websites.

WEBSITE PURPOSE: {purpose}
PRIMARY GOAL: {primary_goal}

WEBSITE ELEMENTS:
{elements}

INSTRUCTIONS:
- Return ONLY valid JSON, no explanation, no markdown, no backticks
- Max 6 scenes total
- Scene types: hero, about, projects, skills, cta, contact, other, noise
- "noise" scenes will be skipped in video — use for nav, footer, cookie, etc.
- "content" is the narration text, max 2 sentences, natural spoken English
- "priority" 10 = show first, 1 = show last
- "duration_hint" is seconds this scene should play (3-8 seconds)
- Order scenes by priority descending

RETURN THIS EXACT FORMAT:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "type": "hero",
      "title": "Introduction",
      "content": "Meet Sumit, a full-stack developer who builds AI-powered tools.",
      "elements": ["Hi I'm Sumit", "View My Work"],
      "priority": 10,
      "duration_hint": 4
    }}
  ]
}}
"""