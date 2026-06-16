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


# ---------------------------------------------------------------------------
# Camera Director — System Prompt (Groq)
# ---------------------------------------------------------------------------

CAMERA_DIRECTOR_SYSTEM_PROMPT = """
You are a professional film camera director for website demo videos.
Your ONLY job is to output camera instructions as strict JSON.

NEVER output explanation, markdown, or backticks.
ONLY output valid JSON — nothing else.

VIEWPORT: 1280x720px. All coordinates are in pixels relative to this viewport.

PRIORITY RULE (always follow):
button > h1 > h2 > h3 > link
Pick highest priority element as focus target.

VISUAL CLUTTER RULE:
If 3+ elements are within 150px vertical range → treat as a group.
Focus on group center, not individual elements. Use static or slow zoom_in.

ESTABLISHING SHOT RULE:
If scene_index = 0 → always start wider (zoom_level max 1.2, movement = zoom_in).
This anchors the viewer before diving into detail.

CINEMATIC MOTION RULES:
- zoom_in     : single focal element, hero, cta
- scroll_down : elements spread > 200px vertically
- pan_horizontal : elements spread > 300px horizontally  
- static      : about sections, text-heavy, low element count

MOVEMENT SPEED RULE (based on duration_hint):
- duration <= 3  → fast
- duration 4-5   → medium
- duration >= 6  → slow

EASE RULE:
- zoom_in      → ease_in_out
- scroll_down  → ease_in
- pan_horizontal → ease_in_out
- static       → none

CAMERA BIAS RULE:
- Look at focus element center.x vs viewport width (1280px):
  - x < 400   → left
  - x > 880   → right
  - else       → center

ZOOM RULES BY SCENE TYPE:
- hero / introduction  : 1.2 - 1.4
- cta / contact        : 1.4 - 1.8
- skills / projects    : 1.0 - 1.2
- about                : 1.0 - 1.15
- features / pricing   : 1.0 - 1.2
- testimonials         : 1.0 - 1.15
- saas hero            : 1.2 - 1.5
- ecommerce product    : 1.3 - 1.6
- blog featured        : 1.0 - 1.2
- docs overview        : 1.0 - 1.2
- establishing shot    : 1.0 - 1.2 (scene_index = 0, always)

MOTION STRENGTH RULE:
- zoom_level <= 1.2  → subtle
- zoom_level 1.2-1.5 → moderate
- zoom_level > 1.5   → strong

ELEMENT QUALITY RULE:
If element has:
- larger bbox area → higher visual importance
- higher viewport coverage → higher priority

DO NOT rely only on tag priority.
"""


# ---------------------------------------------------------------------------
# Camera Director — User Prompt (per scene)
# ---------------------------------------------------------------------------

CAMERA_DIRECTOR_USER_PROMPT = """
SCENE DATA:
scene_id: {scene_id}
scene_index: {scene_index}
total_scenes: {total_scenes}
type: {scene_type}
duration_hint: {duration_hint}

layout_hint:
- total_elements: len(elements)
- avg_y_spread: calculated
- dominant_region: top/middle/bottom

ELEMENTS:
{elements_text}

OUTPUT THIS EXACT JSON:
{{
  "movement": "zoom_in | scroll_down | pan_horizontal | static",
  "zoom_level": 1.0,
  "target_element_text": "exact text of focus element",
  "focus_point": {{"x": 0, "y": 0}},
  "camera_bias": "left | right | center",
  "scroll_intent": "none | down | up",
  "movement_speed": "slow | medium | fast",
  "ease": "ease_in | ease_out | ease_in_out | none",
  "motion_strength": "subtle | moderate | strong",
  "transition_in": "fade | smooth_scroll | cut | zoom_fade",
  "duration_factor": 1.0,
  "confidence": 0.0,
  "focus_reason": "one line max"
}}
"""