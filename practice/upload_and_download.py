from playwright.sync_api import sync_playwright

with sync_playwright() as p :
    try:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        # page.goto("https://demo.automationtesting.in/FileUpload.html")

        ### FILE UPLOADING
        file = r'C:\AI VIDEO GENTERATOR\practice\test.txt'

        # To uploadt anything we use -----> set_input_files method
        page.locator('#input-4').set_input_files(file)

        page.wait_for_timeout(3000)
        page.locator('button[title="Clear selected files"]').click()
        page.wait_for_timeout(2000)
        
        # FILE DOWNLOADING
        page.goto("https://demo.automationtesting.in/FileDownload.html")
        page.locator('#textbox').type("Hello My Name is Sumit")
        page.wait_for_timeout(2000)

        page.locator('#createTxt').click()
        page.wait_for_timeout(2000)

        page.locator('#link-to-download').click()
        page.wait_for_timeout(4000)


    
    except Exception as e :
        print(str(e))