import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p :
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://sumitdev-woad.vercel.app/')
    print("succesffully")
    print(page.title())
    page.wait_for_timeout(3000)
    browser.close()