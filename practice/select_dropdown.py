from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://demo.automationtesting.in/Register.html")

    # steps ---> for select dropdown

    # 1. Find the select Location
    select_dropdown = page.query_selector('#Skills')

    # 2. Select the option

    select_dropdown.select_option(label='Client Support')
    

    # direct method
    page.select_option('#yearbox',label='1947')

    page.wait_for_timeout(5000)