from playwright.sync_api import sync_playwright

def extact_title(page) :
    return page.title()

def exract_heading(page) :
    headings = []

    h1_elements = page.locator("h1")
    count = h1_elements.count()

    for i in range(count):

        heading = h1_elements.nth(i)
        text = heading.text_content()
        headings.append(text)

    return headings

def extract_buttons(page) :
    pass

def extract_links(page) :
    pass

def extract_website_data(url) :
    with sync_playwright() as p :
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            viewport={"width" : 1920 , "height" : 1080}
        )

        page = context.new_page()
        page.goto(url)
        title = extact_title(page)
        headings = exract_heading(page)
        browser.close()

        return {
            "title" : title,
            "heading" : headings
        }

if __name__ == "__main__" :
    url = input("Enter URL : ")
    data = extract_website_data(url)
    print(data)