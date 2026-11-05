from pathlib import Path

import pandas as pd
import requests
import torch
from PIL import Image
from playwright.sync_api import sync_playwright
from transformers import BlipForConditionalGeneration, BlipProcessor

URL = "https://www.facebook.com/ggerendi"
MAX_PHOTOS = 50
IMAGE_DIR = Path("images")
MODEL_NAME = "Salesforce/blip-image-captioning-base"

IMAGE_DIR.mkdir(exist_ok=True)

# Modèle open source exécuté localement : aucun appel à une API payante.
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = BlipProcessor.from_pretrained(MODEL_NAME)
model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)


def describe_image(filename: Path) -> str:
    """Génère une courte description de l'image avec BLIP."""
    image = Image.open(filename).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=50)
    return processor.decode(output[0], skip_special_tokens=True).strip()


reader = __import__("easyocr").Reader(["fr"])
data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    # La page de profil affiche normalement les publications dans l'ordre
    # antéchronologique. On déduplique les URL et garde les 50 premières.
    image_urls = []
    seen_urls = set()
    for img in page.locator("img").all():
        src = img.get_attribute("src")
        if src and "scontent" in src and src not in seen_urls:
            image_urls.append(src)
            seen_urls.add(src)
            if len(image_urls) == MAX_PHOTOS:
                break

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
