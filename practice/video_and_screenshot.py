from playwright.sync_api import sync_playwright
import subprocess

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(record_video_dir='video',
                                  record_video_size={"width": 1920, "height": 1080})
    page = context.new_page()
    page.goto("https://sumitdev-woad.vercel.app/")

    page.screenshot(path=r'video\front_page.png')

    page.get_by_text("View Projects").click()
    
    page.wait_for_timeout(4000)
    page.screenshot(path=r'video\bottom_page.png')

    page.locator('//a[text() ="About"]').click()

    page.wait_for_timeout(3000)
    
    video = page.video
    page.close()
    video.save_as(r'video\demo.webm')
    context.close()
    browser.close()


    