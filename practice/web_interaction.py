from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://demo.automationtesting.in/Selectable.html")

    ### Mouse Actions ----->

    # Hovering
    page.locator('//a[text() = "More"]').hover()

    # click on element
    page.locator('//a[text() = "More"]').click()

    # Double click
    page.locator('//a[text() = "More"]').dblclick()

    # Right click
    page.locator('//a[text() = "More"]').click(button="right")

    # Shift click
    page.locator('//a[text() = "More"]').click(modifiers=["Shift"])

    ### Keyboard Actions --------->
    # Backquote, Minus, Equal, Backslash, Backspace, Tab, Delete, Escape,
    # ArrowDown, End, Enter, Home, Insert, PageDown, PageUp, ArrowRight,
    # ArrowUp, F1 - F12, Digit0 - Digit9, KeyA - KeyZ, etc.
    page.locator('//a[text()="SwitchTo"]').press("A")
    page.wait_for_selector('//a[text()="SwitchTo"]').press("$")

    page.wait_for_timeout(3000)
