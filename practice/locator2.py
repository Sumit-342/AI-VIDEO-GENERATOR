from playwright.sync_api import sync_playwright

with sync_playwright() as play :
    browser = play.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://opensource-demo.orangehrmlive.com/web/index.php/auth/login')

    # xpath ---> relative xpath

    #using attribut ----> //tagname[@attribute_name = "value"]

    # username = page.wait_for_selector('//input[@name="username"]')
    # username.type('Admin')
    # password = page.wait_for_selector('//input[@type="password"]')
    # password.type('admin123')
    # login = page.wait_for_selector('//button[@type="submit"]')
    # login.click()
   

    #using text --> //tagname[text() = "text"]
    # page.wait_for_selector('//p[text() = "Forgot your password? "]').click()

    # contains for :---
    # (i) attributes ---> //tagname[contains(@attribut ,"value")]  
    # (ii) text ---> //tagname[contains(text(),"Forgot your")]

    page.wait_for_selector('//input[contains(text,"username")]').type('admin')

    #family
    # parent --> //tagname[@id = "xy"]/parent :: input
    # child --> //tagname[@id = "xy"]/child :: input
    # sibling --> //tagname[@name='value']//following-sibling::tagname[sibling_number]
    # ancestor -  //tagname[@id = "xy"]/ancestor::input[]

    # dynamic - prasanth123,prasanth13454,prasanth987
    # starts-with - //tagname[starts-with(@id,'prasanth')]
    # ends-with - 2343user
    # family
    # parent - //tagname[@id = "xy"]/parent::input[]
    # child - //tagname[@id = "xy"]/child::input[]
    
  
    page.wait_for_timeout(4000)
    browser.close()