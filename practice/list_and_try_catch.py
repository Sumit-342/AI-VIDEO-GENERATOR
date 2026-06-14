from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try : 
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://demo.automationtesting.in/Selectable.html")

        # Storing multiple elemenst 
        elements = page.locator('b').all_text_contents()

        print(elements)
        print(len(elements))

        for i in elements:
            print(i)
        page.wait_for_timeout(2000)


        # extractring all the links

        links = page.locator('a').all_text_contents()

        print(len(links))

        for i in links:
            print(i)
    except Exception as e :
        print(str(e))

    finally:
        print("Code Executed Successfully")