from playwright.sync_api import sync_playwright
from utils import clean_list , clean_text

def extact_title(page) :
    return page.title()


def exract_heading(page) :
    result = {
        "h1" : [] ,
        "h2" : [] ,
        "h3" : [] ,
    }

    tags = ["h1" , "h2" , "h3"]

    for tag in tags :
        elements = page.locator(tag)
        count = elements.count()

        for i in range(count) :
            element = elements.nth(i)
            text = element.text_content()

            if text :
                result[tag].append(text)
    
    return result


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
    links = []
    link_element = page.locator('a')
    count = link_element.count()

    for i in range(count) :
        element = link_element.nth(i)

        text = element.text_content()
        href = element.get_attribute('href')

        if text :
            text = text.strip()

        if text and href :
            links.append({
                "text" : text,
                "url" : href,
            })


    return links


def extract_website_data(url) :
    with sync_playwright() as p :
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            viewport={"width" : 1920 , "height" : 1080}
        )

        page = context.new_page()
        page.goto(url)

        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)

        # raw extraction

        title = extact_title(page)
        headings = exract_heading(page)
        print(len(headings))

        button = extract_buttons(page)
        print(len(button))

        links = extract_links(page)
        print(len(links))

        # cleaning 
        
        button = clean_list(button)

        headings["h1"] = clean_list(headings["h1"])
        headings["h2"] = clean_list(headings["h2"])
        headings["h3"] = clean_list(headings["h3"])

        clean_link = []

        for link in links :
            text = clean_text(link.get("text"))
            url = link.get("url")

            if text and url :
                clean_link.append({
                    "text" : text ,
                    "url" : url ,
                })

        data =  {
            "title" : title,
            "heading" : headings,
            "buttons" : button ,
            "links" : clean_link ,
        }

        browser.close()
        return data

if __name__ == "__main__" :
    url = input("Enter URL : ")
    data = extract_website_data(url)
    print(data)