from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://demo.automationtesting.in/Alerts.html")

    page.on("dialog", lambda diaglog : print(diaglog.message) or diaglog.accept())
    
    page.locator('a[href = "#CancelTab"]').click()
    
    page.wait_for_timeout(2000)
    
    page.locator('#CancelTab button').click()

    # one more testing

    page.on("dialog",lambda dialog : print(dialog.message) or  dialog.accept("Sumit"))

    page.locator('a[href = "#Textbox"]').click()
    page.wait_for_timeout(2000)
    page.locator('#Textbox button').click()
    
    page.wait_for_timeout(3000)