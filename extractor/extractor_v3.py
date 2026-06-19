import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Page

# ---------------------------------------------------------------------------
# 🚀 Core Pipeline Engine Imports
# ---------------------------------------------------------------------------
from cleaner import clean_website_data
from purpose_engine import detect_purpose
from importance_engine import rank_importance
from scene_builder import attach_coordinates
from camera_engine import generate_camera_plan
from cache_manager import load_cache, set_cache, get_cache, save_cache


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EXTRACT_TAGS = {
    "h1": "h1", 
    "h2": "h2", 
    "h3": "h3",
    "button": "button, [role='button'], input[type='submit']",
    "link": "a[href]"
}
SKIP_LINK_HREFS = {"#", "", "javascript:void(0)", "javascript:"}


# Mega JS Evaluator Script — Single round-trip browser context extractor
MEGA_DOM_EXTRACTOR_JS = """
(selectorsConfig) => {
    const extractedElements = [];
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    function getAbsoluteOffset(node) {
        const rect = node.getBoundingClientRect();
        let scrollYOffset = window.scrollY;
        let scrollXOffset = window.scrollX;
        
        return {
            x: rect.x + scrollXOffset,
            y: rect.y + scrollYOffset,
            width: rect.width,
            height: rect.height,
            rectX: rect.x,
            rectY: rect.y
        };
    }

    for (const [tag, selector] of Object.entries(selectorsConfig)) {
        const nodes = document.querySelectorAll(selector);
        nodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            const style = window.getComputedStyle(node);
            
            const isVisible = (
                rect.width > 2 && 
                rect.height > 2 && 
                style.display !== 'none' && 
                style.visibility !== 'hidden' && 
                parseFloat(style.opacity) !== 0 &&
                rect.left >= -50 && 
                rect.top >= -5000   
            );

            if (!isVisible) return;

            const text = (node.innerText || node.textContent || "").replace(/\\s+/g, ' ').trim();
            if (!text || text.length < 2) return;

            let href = null;
            if (tag === "link") {
                href = node.getAttribute("href");
                if (!href) return;
                href = href.trim();
            }

            const offset = getAbsoluteOffset(node);

            // JS Native push fix
            extractedElements.push({
                tag: tag,
                text: text,
                href: href,
                bbox: {
                    x: Math.round(offset.x),
                    y: Math.round(offset.y),
                    width: Math.round(offset.width),
                    height: Math.round(offset.height)
                }
            });
        });
    }
    return extractedElements;
}
"""


# ---------------------------------------------------------------------------
# Compatibility Layer
# ---------------------------------------------------------------------------
def to_legacy_format(extracted: dict) -> dict:
    h1, h2, h3, buttons, links = [], [], [], [], []

    for el in extracted["elements"]:
        tag, text = el["tag"], el["text"]
        if tag == "h1":
            h1.append(text)
        elif tag == "h2":
            h2.append(text)
        elif tag == "h3":
            h3.append(text)
        elif tag == "button":
            buttons.append(text)
        elif tag == "link":
            links.append({"text": text, "url": el.get("href", "") or ""})

    return {
        "title": extracted["meta"]["title"],
        "heading": {"h1": h1, "h2": h2, "h3": h3},
        "buttons": buttons,
        "links": links,
    }


# ---------------------------------------------------------------------------
# Core Extractor Logic
# ---------------------------------------------------------------------------
async def extract_website_v5(url: str) -> tuple[dict, dict]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        await page.add_init_script("""
            html { scroll-behavior: auto !important; }
            * { overflow-anchor: none !important; }
        """)

        print(f"🚀 Navigating to: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            print("⚠️ Network didn't go fully idle, processing with current DOM state.")

        viewport_height = page.viewport_size["height"]
        step = viewport_height // 2
        
        # Defensive height initialization
        page_height = viewport_height 
        current_y = 0
        max_scroll_limit = 15000 
        
        raw_elements_map = {}

        while current_y < max_scroll_limit:
            try:
                await page.evaluate(f"window.scrollTo(0, {current_y})")
                await page.wait_for_timeout(150) 
                
                batch_elements = await page.evaluate(MEGA_DOM_EXTRACTOR_JS, EXTRACT_TAGS)
                
                for el in batch_elements:
                    if el["tag"] == "link" and el["href"] in SKIP_LINK_HREFS:
                        continue
                    
                    uid_key = f"{el['tag']}_{el['text']}_{el['bbox']['x']}_{el['bbox']['y']}"
                    raw_elements_map[uid_key] = el

                page_height = await page.evaluate("document.body.scrollHeight")
                current_y += step
                if current_y >= page_height:
                    break
            except Exception as loop_err:
                print(f"⚠️ Warning inside scroll sampling loop: {loop_err}")
                break 

        # ===========================================================================
        # 🎯 ADDED HERE: FIX 1 - Spatial Deduplication (Typewriter Killer)
        # ===========================================================================
        spatial_clean_map = {}
        for item in raw_elements_map.values():
            # Tag aur exact X, Y coordinates ke base par unique key banayi
            spatial_key = (item["tag"], item["bbox"]["x"], item["bbox"]["y"])
            
            if spatial_key not in spatial_clean_map:
                spatial_clean_map[spatial_key] = item
            else:
                # Agar coordinate same hai, toh hamesha bada text (fully typed string) rakho
                if len(item["text"]) > len(spatial_clean_map[spatial_key]["text"]):
                    spatial_clean_map[spatial_key] = item
        # ===========================================================================

        final_elements = []
        viewport = page.viewport_size

        # Change: Ab raw_elements_map ki jagah spatial_clean_map par loop chalega
        for item in spatial_clean_map.values():
            bbox = item["bbox"]
            final_elements.append({
                "id": f"el_{uuid.uuid4().hex[:8]}",
                "tag": item["tag"],
                "text": item["text"],
                "href": item["href"],
                "match_key": f"{item['tag']} {item['text']}",
                "bbox": bbox,
                "viewport_coverage": round((bbox["width"] * bbox["height"]) / (viewport["width"] * viewport["height"]), 4),
                "center": {
                    "x": round(bbox["x"] + bbox["width"] / 2, 2),
                    "y": round(bbox["y"] + bbox["height"] / 2, 2),
                },
                "importance_score": None,
                "scene_id": None
            })

        final_elements.sort(key=lambda e: (e["bbox"]["y"], e["bbox"]["x"]))

        await page.evaluate("window.scrollTo(0, 0)")
        title = await page.title()
        await browser.close()

        unified_output = {
            "meta": {
                "url": url,
                "title": title,
                "viewport": viewport,
                "page_height": page_height, 
                "total_elements": len(final_elements),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            },
            "elements": final_elements
        }
        
        legacy_output = to_legacy_format(unified_output)
        return unified_output, legacy_output


# ---------------------------------------------------------------------------
# 🏁 Complete Integrated Main Execution Test Block
# ---------------------------------------------------------------------------
async def _main():
    # 1. Load Local Cache
    load_cache()
    
    url = input("Enter URL: ").strip()
    
    # 2. Run Bulletproof v5 Extractor Engine
    

    unified, legacy = await extract_website_v5(url)
    print(f"\n✅ Extracted {unified['meta']['total_elements']} elements\n")

    # DEBUG — add these 2 lines temporarily
    print("DEBUG first element:", unified['elements'][0] if unified['elements'] else "EMPTY LIST")
    print("DEBUG sample tags:", [el.get('tag') for el in unified['elements'][:5]])

    print(f"\n✅ Extracted {unified['meta']['total_elements']} elements\n")

    # 3. Clean & Sanitize Data
    clean_data = clean_website_data(legacy)

    # 4. Detect Intent/Category
    purpose = detect_purpose(clean_data)

    # 5. Rank Elements & Group Scenes
    scenes = rank_importance(unified, purpose)

    # 6. Map Absolute Visual Rect Coordinates
    enriched_scenes = attach_coordinates(scenes, unified)

    # 7. Generate Consistent Checksum Hash Key
    key = hashlib.md5(
        json.dumps(enriched_scenes, sort_keys=True).encode()
    ).hexdigest()
    
    # 8. Check Cache Store
    cached = get_cache(key)

    if cached:
        print("🔥 CACHE HIT - Skipping Gemini / Director API")
        final = cached
    else:
        print("⚡ CACHE MISS - Calling Gemini / Llama Director Engine")
        final = generate_camera_plan(enriched_scenes)
        set_cache(key, final)

        
        # Optional Rule: Dump state update to physical disk cache file if your manager needs it
        try:
            save_cache()
        except NameError:
            pass

    # 9. Print the Final Cinematic Director Blueprint JSON
    print("\n🎬 FINAL CINEMATIC DIRECTOR SCRIPT LAYOUT:")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())