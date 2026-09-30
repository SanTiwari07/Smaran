"""
Export ppt/index.html to ppt/Smaran_Pitch_Deck.pdf via Playwright.
"""
import io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "ppt" / "index.html"
PDF_PATH = ROOT / "ppt" / "Smaran_Pitch_Deck.pdf"
ROOT_PDF_PATH = ROOT / "ppt.pdf"


def export_pdf():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--force-dark-mode",
                "--background-color=0b0709",
                "--enable-features=WebContentsForceDark",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            color_scheme="dark",
            device_scale_factor=1.5,
        )
        page = context.new_page()
        page.goto(f"file:///{HTML_PATH.resolve()}")
        page.wait_for_timeout(2000)

        # Hide navigation bar and expand stage
        page.evaluate(
            "document.getElementById('nav').style.display = 'none';"
            "document.getElementById('deck').style.height = '100vh';"
        )

        REVIEW_DIR = ROOT / "ppt" / "review_slides"
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)

        frames = []
        for i in range(1, 9):
            page.evaluate(f"showSlide({i})")
            page.wait_for_timeout(500)
            shot_bytes = page.screenshot()
            img = Image.open(io.BytesIO(shot_bytes)).convert("RGB")
            frames.append(img)
            img.save(str(REVIEW_DIR / f"slide_{i}.png"))
            print(f"Captured Slide {i} for PDF and review...")

        frames[0].save(
            str(PDF_PATH),
            save_all=True,
            append_images=frames[1:],
            resolution=150.0,
        )
        # Also copy to root ppt.pdf if desired
        frames[0].save(
            str(ROOT_PDF_PATH),
            save_all=True,
            append_images=frames[1:],
            resolution=150.0,
        )
        browser.close()

    print(f"PDF exported successfully to:\n  - {PDF_PATH}\n  - {ROOT_PDF_PATH}")


if __name__ == "__main__":
    export_pdf()
