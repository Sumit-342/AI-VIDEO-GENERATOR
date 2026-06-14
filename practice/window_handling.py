from playwright.sync_api import sync_playwright


with sync_playwright() as p :
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://demo.automationtesting.in/Windows.html")

    page.locator('#Tabbed a').click()
    page.wait_for_timeout(3000)

    # To find the total numbers of pages

    total_pages = context.pages
    print("Total Pages : ",len(total_pages))

    for i in total_pages:
        print(i)
    

    print("Title OF Parent : ",page.title())
    new_page = total_pages[1]

    # How to switch to new page

    new_page.bring_to_front()
    page.wait_for_timeout(3000)
    print("Title of new page : ",new_page.title())

    new_page.close()
    page.bring_to_front()
    page.wait_for_timeout(3000)
    browser.close()






