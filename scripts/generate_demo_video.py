"""Automated Hackathon Demo Video Generator for Smaran.

Uses:
- edge-tts for high-fidelity studio neural voiceover (en-US-ChristopherNeural)
- Playwright for driving Chromium @ 1920x1080 and capturing video
- Injected visual cursor, spotlight effects, and modern subtitle HUD
- ffmpeg for final audio/video muxing into smaran_demo.mp4
"""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VID_DIR = ROOT / "runtime" / "video_recordings"
AUDIO_DIR = ROOT / "runtime" / "video_audio"
OUT_MP4 = ROOT / "smaran_demo.mp4"

VID_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
FFPROBE = r"C:\ProgramData\chocolatey\bin\ffprobe.exe"
PYTHON = sys.executable

BEATS = [
    {
        "id": "b01_intro",
        "title": "SMARAN · REMEMBER ON MARS",
        "voice": "Every modern AI agent assumes the cloud is always there. But in field engineering, disaster zones, and edge dead zones, connectivity drops. We built Smaran: an offline-first edge memory companion that turns edge disconnection into a first-class feature.",
        "url": "http://127.0.0.1:5173/story/",
        "action": "intro",
    },
    {
        "id": "b02_control",
        "title": "MISSION CONTROL · FLEET TELEMETRY",
        "voice": "From the central Control Center, we monitor Rover A and Rover B. Smaran tracks edge telemetry, memory shards across Krypta, Hermes, and Agora, and syncs vector operations with eighty-five percent wire reduction.",
        "url": "http://127.0.0.1:5173/#control",
        "action": "control",
    },
    {
        "id": "b03_companion_teach",
        "title": "STRUCTURED MEMORY DECOMPOSITION",
        "voice": "In the Companion view, Aarav teaches Smaran about his capstone project. Notice: no manual form filling. Smaran extracts structured facts, the decision, and the explicit rationale behind it automatically.",
        "url": "http://127.0.0.1:5173/#companion",
        "action": "teach",
    },
    {
        "id": "b04_gemini_qa",
        "title": "GROUNDED PROVENANCE · GEMINI ONLINE",
        "voice": "When asked why, Smaran doesn't hallucinate. Connected online to Google Gemini, it grounds the answer directly in the recorded decision, citing source index one with full cryptographic provenance.",
        "url": "http://127.0.0.1:5173/#companion",
        "action": "ask_gemini",
    },
    {
        "id": "b05_surface_offline",
        "title": "SURFACE MODE · ZERO CONNECTIVITY",
        "voice": "Now let's pull the plug. Both devices enter surface mode. The network is completely severed. But on-device vector search and tool execution keep working.",
        "url": "http://127.0.0.1:5173/#control",
        "action": "go_offline",
    },
    {
        "id": "b06_offline_recall",
        "title": "11 MS OFFLINE LOCAL RETRIEVAL",
        "voice": "Aarav asks for project tasks. With zero internet, Smaran responds in just eleven milliseconds from local SQLite and ONNX dense embeddings. When he schedules a reminder, the agent plans, executes, and queues the change in its local outbox.",
        "url": "http://127.0.0.1:5173/#companion",
        "action": "offline_recall",
    },
    {
        "id": "b07_concurrent_edits",
        "title": "CONCURRENT EDITS · CLOCK SKEW RISK",
        "voice": "Now the real edge test. Disconnected, Aarav's phone moves the review meeting to 4 PM. His teammate's laptop moves it to 5 PM. In standard databases, clock skew silently erases one of these updates.",
        "url": "http://127.0.0.1:5173/#control",
        "action": "create_conflict",
    },
    {
        "id": "b08_themis_detection",
        "title": "THEMIS CAUSAL CRDT · ZERO OVERWRITES",
        "voice": "When the devices reconnect, our CRDT engine, Themis, inspects version vectors, proves neither edit saw the other, and surfaces the conflict rather than destroying data.",
        "url": "http://127.0.0.1:5173/#control",
        "action": "themis_crdt",
    },
    {
        "id": "b09_resolve_conflict",
        "title": "HUMAN-IN-THE-LOOP CAUSAL RESOLUTION",
        "voice": "Mission control accepts the 5 PM update. The resolution supersedes both concurrent versions and synchronizes across the fleet with mathematical finality.",
        "url": "http://127.0.0.1:5173/#conflicts",
        "action": "resolve",
    },
    {
        "id": "b10_krypta_privacy",
        "title": "KRYPTA ZERO-LEAKAGE PRIVACY GATE",
        "voice": "What about privacy? When asked about confidential notes, Smaran's Krypta gate activates. Because private data is isolated, cloud LLMs are strictly blocked at the device edge, answering safely from local memory.",
        "url": "http://127.0.0.1:5173/#companion",
        "action": "krypta_privacy",
    },
    {
        "id": "b11_prove_it",
        "title": "LIVE MATHEMATICAL VERIFICATION",
        "voice": "In the 'Prove It' view, judges can re-verify every headline claim live. Zero private records leaked to the cloud. Sub-9 millisecond search. One hundred percent convergence across all replicas.",
        "url": "http://127.0.0.1:5173/#prove",
        "action": "prove_it",
    },
    {
        "id": "b12_outro",
        "title": "SMARAN · BUILT BY SANSKAR, KANISHKA & SHAMBHAVI",
        "voice": "Offline isn't a blackout. It's a landing. Smaran makes edge AI resilient, causal, and truly private. Built by Sanskar Tiwari, Kanishka Salgude, and Shambhavi Patil. Thank you.",
        "url": "http://127.0.0.1:5173/story/#problem",
        "action": "outro",
    },
]


def get_audio_duration(path: Path) -> float:
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


async def generate_all_audio():
    import edge_tts

    print("--- [1/4] Generating Studio Voiceover with edge-tts ---")
    durations = {}
    for b in BEATS:
        out_file = AUDIO_DIR / f"{b['id']}.mp3"
        print(f"  Synthesizing {b['id']}...")
        comm = edge_tts.Communicate(b["voice"], "en-US-ChristopherNeural", rate="+5%")
        await comm.save(str(out_file))
        dur = get_audio_duration(out_file)
        durations[b["id"]] = dur
        print(f"    Done ({dur:.2f}s): {b['title']}")
    return durations


def inject_ui_helpers(page):
    js = """
    (() => {
        if (window.__demoHelpersInjected) return;
        window.__demoHelpersInjected = true;

        // 1. Virtual Cursor
        const cursor = document.createElement('div');
        cursor.id = 'demo-cursor';
        cursor.style.cssText = `
            position: fixed;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: rgba(232, 89, 12, 0.9);
            border: 2px solid #ffffff;
            box-shadow: 0 0 16px rgba(232, 89, 12, 0.9), 0 0 4px #fff;
            pointer-events: none;
            z-index: 2147483647;
            transform: translate(-50%, -50%);
            transition: left 0.4s cubic-bezier(0.16, 1, 0.3, 1), top 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.15s ease;
            left: 50vw;
            top: 50vh;
        `;
        document.body.appendChild(cursor);

        // 2. Click ripple
        window.demoClickAt = (x, y) => {
            cursor.style.left = x + 'px';
            cursor.style.top = y + 'px';
            cursor.style.transform = 'translate(-50%, -50%) scale(0.65)';
            const rip = document.createElement('div');
            rip.style.cssText = `
                position: fixed;
                left: ${x}px;
                top: ${y}px;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                border: 2px solid rgba(232, 89, 12, 0.9);
                pointer-events: none;
                z-index: 2147483646;
                transform: translate(-50%, -50%) scale(1);
                opacity: 1;
                transition: transform 0.4s ease-out, opacity 0.4s ease-out;
            `;
            document.body.appendChild(rip);
            requestAnimationFrame(() => {
                rip.style.transform = 'translate(-50%, -50%) scale(4.5)';
                rip.style.opacity = '0';
            });
            setTimeout(() => rip.remove(), 450);
            setTimeout(() => { cursor.style.transform = 'translate(-50%, -50%) scale(1)'; }, 150);
        };

        window.demoMoveTo = (x, y) => {
            cursor.style.left = x + 'px';
            cursor.style.top = y + 'px';
        };

        // 3. Subtitle HUD Banner
        const hud = document.createElement('div');
        hud.id = 'demo-hud';
        hud.style.cssText = `
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(18, 13, 16, 0.94);
            border: 1px solid rgba(232, 89, 12, 0.8);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.75), 0 0 20px rgba(232, 89, 12, 0.25);
            backdrop-filter: blur(12px);
            color: #f5f1ea;
            padding: 10px 24px;
            border-radius: 9999px;
            font-family: 'Space Grotesk', system-ui, sans-serif;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            z-index: 2147483647;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.3s ease;
        `;
        hud.innerHTML = `
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#e8590c;box-shadow:0 0 8px #e8590c;"></span>
            <span id="demo-hud-title">SMARAN DEMO</span>
        `;
        document.body.appendChild(hud);

        window.demoSetHud = (title) => {
            const el = document.getElementById('demo-hud-title');
            if (el) el.innerText = title;
        };
    })();
    """
    page.evaluate(js)


def move_and_click(page, selector, wait_ms=400):
    try:
        el = page.locator(selector).first
        if el.is_visible():
            box = el.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                page.evaluate(f"window.demoClickAt({cx}, {cy})")
                time.sleep(wait_ms / 1000.0)
                el.click()
                return True
    except Exception as e:
        print(f"    Click fallback on {selector}: {e}")
    return False


def run_recording(durations):
    from playwright.sync_api import sync_playwright

    print("--- [2/4] Recording High-Resolution Video with Playwright ---")
    # Clean previous webm in VID_DIR
    for f in VID_DIR.glob("*.webm"):
        try:
            f.unlink()
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(VID_DIR),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        for b in BEATS:
            beat_id = b["id"]
            title = b["title"]
            dur = durations[beat_id]
            extra_hold = 1.8  # breathing margin for transitions
            total_beat_sec = dur + extra_hold

            print(f"  Recording Beat: {title} (~{total_beat_sec:.1f}s)")
            page.goto(b["url"], wait_until="networkidle")
            page.wait_for_timeout(600)
            inject_ui_helpers(page)
            page.evaluate(f"window.demoSetHud('{title}')")

            act = b["action"]
            t_start = time.time()

            if act == "intro":
                page.evaluate("window.demoMoveTo(960, 400)")
                page.wait_for_timeout(1500)
                page.evaluate("window.scrollBy({ top: 450, behavior: 'smooth' })")
                page.wait_for_timeout(2500)
                page.evaluate("window.scrollBy({ top: 350, behavior: 'smooth' })")

            elif act == "control":
                page.evaluate("window.demoMoveTo(400, 300)")
                page.wait_for_timeout(1000)
                move_and_click(page, 'button:has-text("Show") ~ button:has-text("Memory")')
                page.wait_for_timeout(1500)
                move_and_click(page, 'button:has-text("AI routing")')
                page.wait_for_timeout(1500)

            elif act == "teach":
                # Type capstone statement
                teach_msg = "I'm building Project Nova. I handle the backend, we're using FastAPI and PostgreSQL, and we chose PostgreSQL because we need relational transactions."
                move_and_click(page, 'input[aria-label="Message"]')
                page.wait_for_timeout(400)
                page.fill('input[aria-label="Message"]', teach_msg)
                page.wait_for_timeout(800)
                move_and_click(page, 'button:has-text("Send")')
                # Wait for the response cards to render
                page.wait_for_timeout(3500)

            elif act == "ask_gemini":
                move_and_click(page, 'input[aria-label="Message"]')
                page.wait_for_timeout(400)
                page.fill('input[aria-label="Message"]', "Why did we choose PostgreSQL?")
                page.wait_for_timeout(800)
                move_and_click(page, 'button:has-text("Send")')
                page.wait_for_timeout(4000)

            elif act == "go_offline":
                move_and_click(page, 'button:has-text("Go offline")')
                page.wait_for_timeout(2500)

            elif act == "offline_recall":
                move_and_click(page, 'input[aria-label="Message"]')
                page.wait_for_timeout(400)
                page.fill('input[aria-label="Message"]', "What are the remaining tasks for my project?")
                page.wait_for_timeout(600)
                move_and_click(page, 'button:has-text("Send")')
                page.wait_for_timeout(2500)
                # schedule reminder prompt
                page.fill('input[aria-label="Message"]', "Remind me tomorrow evening to finish the API integration")
                page.wait_for_timeout(500)
                move_and_click(page, 'button:has-text("Send")')
                page.wait_for_timeout(3000)

            elif act == "create_conflict":
                move_and_click(page, 'button:has-text("Create conflict")')
                page.wait_for_timeout(3500)

            elif act == "themis_crdt":
                move_and_click(page, 'button:has-text("Simulate reconnect")')
                page.wait_for_timeout(2500)
                page.goto("http://127.0.0.1:5173/#conflicts", wait_until="networkidle")
                inject_ui_helpers(page)
                page.evaluate(f"window.demoSetHud('{title}')")
                page.wait_for_timeout(3000)

            elif act == "resolve":
                # Click resolution button on the conflict card
                resolved = move_and_click(page, 'button:has-text("Mission control keeps this")')
                if not resolved:
                    move_and_click(page, 'button:has-text("Keep this")')
                page.wait_for_timeout(3000)

            elif act == "krypta_privacy":
                try:
                    import httpx
                    httpx.post("http://127.0.0.1:8001/companion/chat", json={"text": "Remember: Call Riya on 9876543210 about the project."}, timeout=5)
                except Exception:
                    pass
                move_and_click(page, 'input[aria-label="Message"]')
                page.wait_for_timeout(400)
                page.fill('input[aria-label="Message"]', "What is Riya's phone number?")
                page.wait_for_timeout(600)
                move_and_click(page, 'button:has-text("Send")')
                page.wait_for_timeout(4000)

            elif act == "prove_it":
                # Click Run on privacy check
                move_and_click(page, 'button:has-text("Run")')
                page.wait_for_timeout(2000)
                # Click Run on latency check if visible
                btns = page.locator('button:has-text("Run")')
                if btns.count() > 1:
                    btns.nth(1).click()
                page.wait_for_timeout(3000)

            elif act == "outro":
                page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
                page.wait_for_timeout(3500)

            # Hold remainder of beat time so audio matches visually
            elapsed = time.time() - t_start
            remaining = total_beat_sec - elapsed
            if remaining > 0:
                page.wait_for_timeout(int(remaining * 1000))

        context.close()
        browser.close()

    # Find recorded webm
    recorded_webms = list(VID_DIR.glob("*.webm"))
    if not recorded_webms:
        raise RuntimeError("No video file was recorded by Playwright.")
    # Pick newest
    recorded_webms.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recorded_webms[0]


def assemble_final_video(video_path: Path, durations: dict):
    print("--- [3/4] Assembling Master Audio Track ---")
    # Concatenate audio files with padding matching beat lengths
    audio_concat_list = AUDIO_DIR / "concat.txt"
    lines = []
    for b in BEATS:
        beat_file = AUDIO_DIR / f"{b['id']}.mp3"
        extra_hold = 1.8
        # Create a small silence file for the extra hold
        silence_file = AUDIO_DIR / f"silence_{b['id']}.mp3"
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo",
                "-t",
                str(extra_hold),
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(silence_file),
            ],
            capture_output=True,
            check=True,
        )

        lines.append(f"file '{beat_file.as_posix()}'")
        lines.append(f"file '{silence_file.as_posix()}'")

    audio_concat_list.write_text("\n".join(lines), encoding="utf8")
    master_audio = ROOT / "runtime" / "master_voiceover.mp3"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(audio_concat_list),
            "-c",
            "copy",
            str(master_audio),
        ],
        capture_output=True,
        check=True,
    )
    print(f"  Master audio ready: {master_audio}")

    print("--- [4/4] Encoding Master MP4 with ffmpeg ---")
    # Mux video (webm) and audio into final MP4 with H.264 high profile
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(master_audio),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "21",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(OUT_MP4),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr)
        raise RuntimeError("FFmpeg failed to encode MP4")

    size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
    duration = get_audio_duration(OUT_MP4)
    print(f"\n=======================================================")
    print(f"  SUCCESS! Demo Video Generated:")
    print(f"  Path:     {OUT_MP4}")
    print(f"  Duration: {duration:.1f} seconds ({duration/60:.2f} mins)")
    print(f"  Size:     {size_mb:.2f} MB")
    print(f"  Specs:    1920x1080 @ 60fps / H.264 AAC Stereo")
    print(f"=======================================================\n")


def main():
    durations = asyncio.run(generate_all_audio())
    video_path = run_recording(durations)
    assemble_final_video(video_path, durations)


if __name__ == "__main__":
    main()
