from playwright.sync_api import sync_playwright
import requests
import os
import pandas as pd
import easyocr

URL = "https://www.facebook.com/ggerendi"

os.makedirs("images", exist_ok=True)

reader = easyocr.Reader(['fr'])

data = []

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

            filename = f"images/image_{compteur}.jpg"

            try:

                response = requests.get(src, timeout=30)

                with open(filename, "wb") as f:
                    f.write(response.content)

                texte = ""

                try:
                    result = reader.readtext(filename)

                    texte = " ".join(
                        [item[1] for item in result]
                    )

                except:
                    texte = ""

                data.append({
                    "image": filename,
                    "texte": texte
                })

            except Exception as e:
                print(e)

    browser.close()

pd.DataFrame(data).to_csv(
    "resultats.csv",
    index=False
)

print("CSV généré")
