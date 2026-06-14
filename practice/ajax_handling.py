from playwright.sync_api import sync_playwright

with sync_playwright() as p :
    try :
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.plus2net.com/php_tutorial/ajax_drop_down_list-demo.php")

        page.locator('#s1').select_option('Games')
        page.locator('#s2').select_option('Baseball')
        page.wait_for_timeout(3000)


    except Exception as e :
        print(str(e))

    finally:
        print("Code Excuted")