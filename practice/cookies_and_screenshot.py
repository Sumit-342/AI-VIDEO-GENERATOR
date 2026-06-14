from playwright.sync_api import sync_playwright

with sync_playwright() as p :
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto('https://www.redbus.in/')   # for cookie testing
    page.goto('https://sumitdev-woad.vercel.app/')  # for the screenshot website 

    # Gives cookies
    my_cookies = page.context.cookies()

    print(my_cookies)


    # clear cookies

    page.context.clear_cookies()

    # To pass the new cookies to the page

    new_cookies = {
        'name' : 'sumit',
        'id' : '75853'
    }

    page.context.add_cookies([new_cookies])

    # Taking Screenshot

    page.screenshot(path='sample.png',full_page=True)

