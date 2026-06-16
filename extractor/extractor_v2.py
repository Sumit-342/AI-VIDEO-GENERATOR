import asyncio
import json
import uuid
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Page, ElementHandle
from importance_engine import rank_importance
from purpose_engine import detect_purpose
from cleaner import clean_website_data
from scene_builder import attach_coordinates

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EXTRACT_TAGS = {
    "h1":     "h1",
    "h2":     "h2",
    "h3":     "h3",
    "button": "button, [role='button'], input[type='submit']",
    "link":   "a[href]",
}

# Links to skip — not useful for camera planning or video
SKIP_LINK_HREFS = {"#", "", "javascript:void(0)", "javascript:"}


# ---------------------------------------------------------------------------
# Single element extractor — text + bbox in ONE DOM touch
# ---------------------------------------------------------------------------

async def _extract_element(el: ElementHandle, tag: str,viewport : dict) -> dict | None:
    """
    Extract text and bounding box from a single element in one pass.
    Returns None if element is invisible or has no meaningful text.
    """
    try:
        # Scroll into view — required for off-screen elements

        try :
            await el.scroll_into_view_if_needed(timeout=500)
        except : 
            pass

        # Get text and bbox in parallel — single DOM round trip each
        text_raw = await el.inner_text()
        bbox     = await el.bounding_box()
        
        href = None

        print(
            f"TAG={tag} | TEXT ='{text_raw[:40]}' | BBOX ={bbox} "
        )

        # Skip invisible elements
        if bbox is None:
            print(f"rejected {tag} -> bbox none")
            return None

        text = " ".join(text_raw.split()).strip()
        if not text or len(text) < 2:
            print(f"rejected {tag} --> empty text")
            return None

        # For links — skip href-less or javascript links
        if tag == "link":
            href = await el.get_attribute("href") or ""
            href = href.strip()
            if href in SKIP_LINK_HREFS or href.startswith("javascript:"):
                return None

        return {
            "id":    f"el_{uuid.uuid4().hex[:8]}",
            "tag":   tag,
            "text":  text,
            "href" : href ,
            "match_key" : f"{tag} {text}",
            "bbox": {
                "x":      round(bbox["x"]),
                "y":      round(bbox["y"]),
                "width":  round(bbox["width"]),
                "height": round(bbox["height"]),
            },
            
            "viewport_coverage": round(
                (bbox["width"] * bbox["height"]) / (viewport["width"] * viewport["height"]),
                4
            ),
            "center": {
                "x": round(bbox["x"] + bbox["width"] / 2, 2),
                "y": round(bbox["y"] + bbox["height"] / 2, 2),
            },

            # Future fields — populated downstream by importance engine
            "importance_score": None,
            "scene_id":         None,
        }

    except Exception as e:
        print(f"Error {tag} : {e}")
        return None


# ---------------------------------------------------------------------------
# Page extractor — all tags, one Playwright pass
# ---------------------------------------------------------------------------

async def _extract_page(page: Page, url: str) -> dict:
    """
    Extract all elements with bbox from a loaded page.
    Single Playwright pass — no duplicate DOM lookups.
    """
    viewport = page.viewport_size or {"width": 1280, "height": 720}
    title    = await page.title()
    elements = []

    

    for tag, selector in EXTRACT_TAGS.items():
        handles = await page.query_selector_all(selector)

        print(f"{tag} : {len(handles)}")

        for el in handles:
            extracted = await _extract_element(el, tag ,viewport)
            if extracted:
                elements.append(extracted)

    # Sort by vertical position — natural reading/camera order
    elements.sort(key=lambda e: (e["bbox"]["y"], e["bbox"]["x"]))

    return {
        "meta": {
            "url":          url,
            "title":        title,
            "viewport":     viewport,
            "total_elements": len(elements),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        },
        "elements": elements,
    }


# ---------------------------------------------------------------------------
# Compatibility layer — cleaner + purpose engine expect old format
# ---------------------------------------------------------------------------

def to_legacy_format(extracted: dict) -> dict:
    """
    Convert unified elements → old {title, heading, buttons, links} format.
    Keeps full pipeline (cleaner → purpose → importance) working unchanged.
    """
    h1, h2, h3, buttons, links = [], [], [], [], []

    for el in extracted["elements"]:
        tag  = el["tag"]
        text = el["text"]
        if tag == "h1":
            h1.append(text)
        elif tag == "h2":
            h2.append(text)
        elif tag == "h3":
            h3.append(text)
        elif tag == "button":
            buttons.append(text)
        elif tag == "link":
            links.append({"text": text, "url": ""})

    return {
        "title":   extracted["meta"]["title"],
        "heading": {"h1": h1, "h2": h2, "h3": h3},
        "buttons": buttons,
        "links":   links,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def extract_website(url: str) -> tuple[dict, dict]:
    """
    Extract website elements with bounding boxes.

    Returns:
        (unified_data, legacy_data)
        - unified_data → for camera planning, scene mapping, video generation
        - legacy_data  → for cleaner → purpose → importance pipeline (unchanged)
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page    = await browser.new_page(viewport={"width": 1280, "height": 720})

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Let JS render finish
        await page.wait_for_timeout(1500)

        unified = await _extract_page(page, url)
        legacy  = to_legacy_format(unified)

        await browser.close()
        return unified, legacy


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

async def _main():
    url = input("Enter URL: ").strip()
    unified, legacy = await extract_website(url)

    print(f"\n✅ Extracted {unified['meta']['total_elements']} elements\n")

    clean_data = clean_website_data(legacy)

    purpose = detect_purpose(clean_data)

    scenes = rank_importance(clean_data , purpose)

    enriched_scenes = attach_coordinates(scenes ,unified)
    print(json.dumps(enriched_scenes , indent=2))
    


if __name__ == "__main__":
    asyncio.run(_main())