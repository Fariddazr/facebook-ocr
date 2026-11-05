from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import easyocr
import pandas as pd
import requests
import torch
from PIL import Image
from playwright.sync_api import sync_playwright
from transformers import BlipForConditionalGeneration, BlipProcessor

URL = "https://www.facebook.com/ggerendi"
MAX_PHOTOS = 50
MAX_SCROLLS = 80
NO_GROWTH_LIMIT = 6
SCROLL_WAIT_MS = 1500
IMAGE_DIR = Path("images")
MODEL_NAME = "Salesforce/blip-image-captioning-base"

IMAGE_DIR.mkdir(exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
processor = BlipProcessor.from_pretrained(MODEL_NAME)
model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)


def describe_image(filename: Path) -> str:
    image = Image.open(filename).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=50)
    return processor.decode(output[0], skip_special_tokens=True).strip()


def image_key(src: str) -> str:
    parts = urlsplit(src)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def collect_image_urls(page) -> list[str]:
    urls_by_key = {}
    no_growth_rounds = 0

    for _ in range(MAX_SCROLLS):
        visible_urls = page.locator("img").evaluate_all(
            "imgs => imgs.map(img => img.currentSrc || img.src)"
        )
        old_count = len(urls_by_key)

        for src in visible_urls:
            if src and "scontent" in src:
                urls_by_key.setdefault(image_key(src), src)
                if len(urls_by_key) >= MAX_PHOTOS:
                    break

        if len(urls_by_key) >= MAX_PHOTOS:
            break

        if len(urls_by_key) == old_count:
            no_growth_rounds += 1
        else:
            no_growth_rounds = 0

        if no_growth_rounds >= NO_GROWTH_LIMIT:
            break

        page.evaluate("window.scrollBy(0, Math.max(window.innerHeight * 0.8, 600))")
        page.wait_for_timeout(SCROLL_WAIT_MS)

    return list(urls_by_key.values())[:MAX_PHOTOS]


reader = easyocr.Reader(["fr"])
data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    image_urls = collect_image_urls(page)
    print(f"{len(image_urls)} URL(s) d'image trouvée(s) après défilement.")

    for index, src in enumerate(image_urls, start=1):
        filename = IMAGE_DIR / f"image_{index:02d}.jpg"
        try:
            response = requests.get(src, timeout=30)
            response.raise_for_status()
            filename.write_bytes(response.content)

            texte = ""
            description = ""
            try:
                texte = " ".join(item[1] for item in reader.readtext(str(filename)))
            except Exception as error:
                print(f"Erreur OCR pour {filename}: {error}")

            try:
                description = describe_image(filename)
            except Exception as error:
                print(f"Erreur d'analyse IA pour {filename}: {error}")

            print(f"{filename}: description={description!r}, texte={texte!r}")
            data.append({
                "image": str(filename),
                "description_ia": description,
                "texte_ocr": texte,
            })
        except Exception as error:
            print(f"Erreur pour l'image {src}: {error}")

    browser.close()

pd.DataFrame(data).to_csv("resultats.csv", index=False, encoding="utf-8-sig")
print(f"CSV généré : {len(data)} image(s) analysée(s), maximum {MAX_PHOTOS}.")
