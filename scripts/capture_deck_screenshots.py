"""
Captures authentic, high-resolution screenshots from the running Smaran application.
Uses exact hash routes (#control, #memory, #conflicts, #prove, #companion).
"""
import io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / "ppt" / "screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def capture_all():
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

        # 1. Hero: Control Center
        print("Capturing 01_control_center.png (#control)...")
        page.goto("http://127.0.0.1:5173/#control", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "01_control_center.png"))

        # 2. Companion Chat with Grounded Gemini Citation (Online Mode)
        print("Capturing 02_companion_grounded.png (#companion)...")
        page.goto("http://127.0.0.1:5173/#companion", wait_until="networkidle")
        page.wait_for_timeout(1000)
        try:
            rec_btn = page.locator("button:has-text('Reconnect')").first
            if rec_btn.count() > 0:
                rec_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            pass
        # Click one of the suggestions to get an immediate grounded answer
        try:
            sug = page.locator("button:has-text('Why did we choose PostgreSQL?')").first
            if sug.count() > 0:
                sug.click()
                page.wait_for_timeout(4500)
        except Exception:
            pass
        page.screenshot(path=str(SHOT_DIR / "02_companion_grounded.png"))

        # 3. Companion in Offline Surface Mode
        print("Capturing 03_companion_offline.png (#companion offline)...")
        try:
          off_btn = page.locator("button:has-text('Go offline')").first
          if off_btn.count() > 0:
              off_btn.click()
              page.wait_for_timeout(1500)
        except Exception:
          pass
        page.screenshot(path=str(SHOT_DIR / "03_companion_offline.png"))

        # Reconnect
        try:
          rec_btn = page.locator("button:has-text('Reconnect')").first
          if rec_btn.count() > 0:
              rec_btn.click()
              page.wait_for_timeout(1000)
        except Exception:
          pass

        # 4. Memory and Search (Explorer)
        print("Capturing 04_memory_explorer.png (#memory)...")
        page.goto("http://127.0.0.1:5173/#memory", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "04_memory_explorer.png"))

        # 5. Themis Conflicts & Decisions
        print("Capturing 05_conflicts_themis.png (#conflicts)...")
        # First trigger a conflict simulation if possible
        page.goto("http://127.0.0.1:5173/#control", wait_until="networkidle")
        page.wait_for_timeout(1500)
        try:
          sim_btn = page.locator("button:has-text('Simulate conflict'), button:has-text('Inject conflict')").first
          if sim_btn.count() > 0:
              sim_btn.click()
              page.wait_for_timeout(1500)
        except Exception:
          pass
        page.goto("http://127.0.0.1:5173/#conflicts", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "05_conflicts_themis.png"))

        # 6. Prove It Benchmarks
        print("Capturing 06_prove_it_benchmarks.png (#prove)...")
        page.goto("http://127.0.0.1:5173/#prove", wait_until="networkidle")
        page.wait_for_timeout(2000)
        try:
          run_btn = page.locator("button:has-text('Run all'), button:has-text('Run tests')").first
          if run_btn.count() > 0:
              run_btn.click()
              page.wait_for_timeout(4000)
        except Exception:
          pass
        page.screenshot(path=str(SHOT_DIR / "06_prove_it_benchmarks.png"))

        browser.close()

    # Now create high-impact focused crops
    print("Generating focused crops...")
    # 02 crop
    im2 = Image.open(SHOT_DIR / "02_companion_grounded.png")
    w, h = im2.size
    im2.crop((int(w * 0.10), int(h * 0.12), int(w * 0.90), int(h * 0.88))).save(
        SHOT_DIR / "02_companion_online_crop.png"
    )

    # 03 crop
    im3 = Image.open(SHOT_DIR / "03_companion_offline.png")
    im3.crop((int(w * 0.10), int(h * 0.12), int(w * 0.90), int(h * 0.88))).save(
        SHOT_DIR / "03_companion_offline_crop.png"
    )

    # 04 crop
    im4 = Image.open(SHOT_DIR / "04_memory_explorer.png")
    im4.crop((int(w * 0.05), int(h * 0.10), int(w * 0.95), int(h * 0.90))).save(
        SHOT_DIR / "04_memory_crop.png"
    )

    # 05 crop
    im5 = Image.open(SHOT_DIR / "05_conflicts_themis.png")
    im5.crop((int(w * 0.05), int(h * 0.10), int(w * 0.95), int(h * 0.90))).save(
        SHOT_DIR / "05_conflicts_crop.png"
    )

    # 06 crop
    im6 = Image.open(SHOT_DIR / "06_prove_it_benchmarks.png")
    im6.crop((int(w * 0.05), int(h * 0.10), int(w * 0.95), int(h * 0.90))).save(
        SHOT_DIR / "06_prove_it_crop.png"
    )
    print("All authentic screenshots captured and cropped successfully!")


if __name__ == "__main__":
    capture_all()
