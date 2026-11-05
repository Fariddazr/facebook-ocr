from playwright.sync_api import sync_playwright

URL = "https://www.facebook.com/ggerendi"

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    page.goto(URL, wait_until="networkidle")

    page.wait_for_timeout(5000)

    images = page.locator("img").all()

    print(f"Nombre d'images trouvées : {len(images)}")

    for i, img in enumerate(images):

        src = img.get_attribute("src")

        if src:
            print(f"\nIMAGE {i+1}")
            print(src)

    browser.close()
