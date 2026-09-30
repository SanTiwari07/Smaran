"""
Capture authentic, high-resolution screenshots from the running Smaran application.
Outputs into ppt/screenshots/.
"""
from pathlib import Path
import time
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
        page.add_init_script(
            "document.documentElement.style.backgroundColor = '#0b0709';"
            "document.body.style.backgroundColor = '#0b0709';"
        )

        # 1. Hero / Control Center
        print("Capturing 01_control_center.png...")
        page.goto("http://127.0.0.1:5173/control", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "01_control_center.png"))

        # 2. Companion Chat with Grounded Gemini Citation & Thought Trace
        print("Capturing 02_companion_grounded.png...")
        page.goto("http://127.0.0.1:5173/companion", wait_until="networkidle")
        page.wait_for_timeout(1500)
        # Type realistic input
        input_box = page.locator("textarea, input[type='text']").first
        if input_box.count() > 0:
            input_box.fill("Where is the backup oxygen valve and what is the torque spec?")
            send_btn = page.locator("button:has-text('Send'), button[type='submit']").first
            if send_btn.count() > 0:
                send_btn.click()
                page.wait_for_timeout(3500)
        # Expand provenance/reasoning if button present
        try:
            prov_btn = page.locator("button:has-text('Why did Smaran say this?'), button:has-text('Provenance'), button:has-text('Sources')").first
            if prov_btn.count() > 0:
                prov_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass
        page.screenshot(path=str(SHOT_DIR / "02_companion_grounded.png"))

        # 3. Companion in Offline Surface Mode with Task Queue
        print("Capturing 03_companion_offline.png...")
        # Toggle surface mode via Control Center
        page.goto("http://127.0.0.1:5173/control", wait_until="networkidle")
        page.wait_for_timeout(1500)
        try:
            offline_btn = page.locator("button:has-text('Go offline')").first
            if offline_btn.count() > 0:
                offline_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            pass
        # Return to companion
        page.goto("http://127.0.0.1:5173/companion", wait_until="networkidle")
        page.wait_for_timeout(1500)
        input_box = page.locator("textarea, input[type='text']").first
        if input_box.count() > 0:
            input_box.fill("Schedule solar array maintenance for 08:00 UTC")
            send_btn = page.locator("button:has-text('Send'), button[type='submit']").first
            if send_btn.count() > 0:
                send_btn.click()
                page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "03_companion_offline.png"))

        # 4. Memory Explorer (Tri-Shard Partitioning)
        print("Capturing 04_memory_explorer.png...")
        page.goto("http://127.0.0.1:5173/explorer", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "04_memory_explorer.png"))

        # 5. Themis Causal CRDT Conflicts & Decisions
        print("Capturing 05_conflicts_themis.png...")
        # Simulate conflict from control center first
        page.goto("http://127.0.0.1:5173/control", wait_until="networkidle")
        page.wait_for_timeout(1000)
        try:
            conflict_btn = page.locator("button:has-text('Create conflict')").first
            if conflict_btn.count() > 0:
                conflict_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            pass
        page.goto("http://127.0.0.1:5173/conflicts", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "05_conflicts_themis.png"))

        # 6. Prove It (Reproducible Mathematical Benchmark Suite)
        print("Capturing 06_prove_it_benchmarks.png...")
        page.goto("http://127.0.0.1:5173/prove", wait_until="networkidle")
        page.wait_for_timeout(2000)
        try:
            run_btn = page.locator("button:has-text('Run all'), button:has-text('Run')").first
            if run_btn.count() > 0:
                run_btn.click()
                page.wait_for_timeout(3500)
        except Exception:
            pass
        page.screenshot(path=str(SHOT_DIR / "06_prove_it_benchmarks.png"))

        # 7. Reconnect & Reset demo state
        page.goto("http://127.0.0.1:5173/control", wait_until="networkidle")
        page.wait_for_timeout(1000)
        try:
            recon_btn = page.locator("button:has-text('Simulate reconnect')").first
            if recon_btn.count() > 0:
                recon_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # 8. Mars Scrollytelling Visualizer
        print("Capturing 07_story_mars.png...")
        page.goto("http://127.0.0.1:5173/story/", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOT_DIR / "07_story_mars.png"))

        browser.close()
    print("All authentic screenshots successfully captured into ppt/screenshots/!")


if __name__ == "__main__":
    capture_all()
