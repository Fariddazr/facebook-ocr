from playwright.sync_api import sync_playwright

URL = "https://www.facebook.com/ggerendi"

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    page.goto(URL, wait_until="networkidle")

    print("Titre :", page.title())

    print("URL finale :", page.url)

    browser.close()
