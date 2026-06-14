from playwright.sync_api import sync_playwright

with sync_playwright() as p :
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://demo.automationtesting.in/Register.html")
    # page.goto('https://quotes.toscrape.com/')

    # Radio Button , we can use click() or check() any of them 

    page.locator('input[value="Male"]').click()

    # # checkboxes 

    page.locator('#checkbox1').check()
    page.locator('#checkbox3').check()


    # quotes scrapping
    
    quotes = page.locator('.quote').all_text_contents()
    for quote in quotes :
        print(quote)
        

    page.wait_for_timeout(3000)