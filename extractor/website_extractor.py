from playwright.sync_api import sync_playwright

def extact_title(page) :
    return page.title()

def exract_heading(page) :
    heading = []
    tags = ["h1" , "h2" , "h3"]

    for tag in tags :
        elements = page.locator(tag)
        count = elements.count()

        for i in range(count) :
            element = elements.nth(i)
            text = element.text_content()

            if text :
                heading.append(text.strip())
    
    return heading


def extract_buttons(page) :
    buttons = []

    button_element = page.locator('button')
    count = button_element.count()

    for i in range(count) :
        button = button_element.nth(i)
        text = button.text_content()

        if text :
            buttons.append(text.strip())

    return buttons

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
        print(len(headings))
        button = extract_buttons(page)
        print(len(button))
        browser.close()

        return {
            "title" : title,
            "heading" : headings,
            "buttons" : button ,
        }

if __name__ == "__main__" :
    url = input("Enter URL : ")
    data = extract_website_data(url)
    print(data)