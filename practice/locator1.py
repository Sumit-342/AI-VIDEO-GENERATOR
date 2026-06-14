from playwright.sync_api import sync_playwright
import re

with sync_playwright() as play :
    browser = play.chromium.launch(headless=False)
    page = browser.new_page()
    # page.goto("https://demo.automationtesting.in/")
    page.goto('https://opensource-demo.orangehrmlive.com/web/index.php/auth/login')

    # -> id ,. -> class ,tagname,[]-> atrribute for css selector 

    # using ID

    email_txt = page.wait_for_selector('#email')
    email_txt.type('sumitsingh.connect@gmail.com')
    print(page.title())
    buttton_click = page.wait_for_selector('#enterimg')
    buttton_click.click()
    page.wait_for_timeout(3000)
    browser.close()

    #using attribute

    username = page.wait_for_selector('input[name="username"]')
    username.type('Admin')
    login = page.wait_for_selector('input[name="password"]')
    login.type('admin123')
    button_click = page.wait_for_selector('button[type="submit"]')
    button_click.click()
    page.wait_for_timeout(3000)
    browser.close()
    