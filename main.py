from playwright.sync_api import sync_playwright
import requests
import os

URL = "https://www.facebook.com/ggerendi"

os.makedirs("images", exist_ok=True)

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    page.goto(URL, wait_until="networkidle")

    page.wait_for_timeout(5000)

    images = page.locator("img").all()

    compteur = 0

    for img in images:

        src = img.get_attribute("src")

        if src and "scontent" in src:

            compteur += 1

            print(f"Téléchargement image {compteur}")

            try:

                response = requests.get(src, timeout=30)

                with open(
                    f"images/image_{compteur}.jpg",
                    "wb"
                ) as f:

                    f.write(response.content)

            except Exception as e:
                print(e)

    browser.close()

print(f"Images téléchargées : {compteur}")
