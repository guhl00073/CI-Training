#!/usr/bin/env python3
"""
Auto-screenshot tool for CI-Hörtrainer user guide.
Uses Selenium with the Safari/Chrome WebDriver if available, else falls back
to a URL-based screenshot approach via playwright.
Run: python3 scripts/capture_screenshots_py.py
"""

import subprocess, time, os, sys, urllib.request, json

BASE_URL = "http://localhost:8080"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
os.makedirs(OUT_DIR, exist_ok=True)

def run_js_in_browser(url, js_actions, output_path):
    """Use osascript to control Chrome/Safari to capture screenshot."""
    apple_script = f"""
tell application "Google Chrome"
    set theTab to make new tab at end of tabs of window 1
    set URL of theTab to "{url}"
    delay 2
    {js_actions}
    delay 1
end tell
tell application "System Events"
    delay 0.5
end tell
do shell script "screencapture -x '{output_path}'"
"""
    result = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ osascript error: {result.stderr[:100]}")
    else:
        print(f"  ✅ {os.path.basename(output_path)}")

def capture_via_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    
    print("Using playwright for screenshots...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        def shot(filename, delay=1.0):
            time.sleep(delay)
            page.screenshot(path=os.path.join(OUT_DIR, filename), full_page=False)
            print(f"  ✅ {filename}")

        # Clear local storage for consistent state
        page.goto(BASE_URL, wait_until="networkidle")
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="networkidle")
        
        # 1. Dashboard
        shot("dashboard.png", delay=1.5)

        # 2. Audio settings expanded
        page.goto(BASE_URL, wait_until="networkidle")
        for sel in ["#controlPanelDetails summary", ".ctrl-summary"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    time.sleep(0.8)
                    break
            except:
                pass
        shot("audio_settings.png", delay=1.0)

        # Voice dropdown
        try:
            vs = page.locator("#voiceSelect")
            if vs.is_visible():
                vs.select_option(index=3)
                time.sleep(0.4)
                shot("voice_selection.png")
        except:
            pass

        # 3. Profile modal
        page.goto(BASE_URL, wait_until="networkidle")
        for sel in ["#profileBtn", "#headerProfileBtn", "button.profile-btn"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    time.sleep(0.7)
                    break
            except:
                pass
        shot("profiles.png")
        page.keyboard.press("Escape")
        time.sleep(0.4)

        # 3.5. Therapist Report modal
        page.goto(BASE_URL, wait_until="networkidle")
        for sel in ["#openTherapistReportBtn", "button[onclick*='openTherapistReport']"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    time.sleep(1.0)
                    break
            except:
                pass
        shot("therapist_report.png")
        page.keyboard.press("Escape")
        time.sleep(0.4)

        # 4. Module tabs
        tabs = [
            ("mp",        "module_minimal_pairs.png"),
            ("es",        "module_einsilber.png"),
            ("ms",        "module_mehrsilber.png"),
            ("num",       "module_zahlen.png"),
            ("sent",      "module_saetze.png"),
            ("olsa",      "module_olsa.png"),
            ("noise",     "module_stoerschall.png"),
            ("memory",    "module_gedaechtnis.png"),
            ("weakness",  "module_schwachstellen.png"),
            ("audiogram", "module_audiogramm.png"),
            ("stats",     "module_statistik.png"),
            ("editor",    "module_editor.png"),
        ]
        for tab_id, filename in tabs:
            try:
                clicked = False
                for sel in [f"[data-tab='{tab_id}']", f"#nav-{tab_id}", f".tab-btn[data-tab='{tab_id}']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible():
                            el.click()
                            clicked = True
                            break
                    except:
                        pass
                if not clicked:
                    # Try JS eval
                    page.evaluate(f"document.querySelector('[data-tab=\"{tab_id}\"]')?.click()")
                shot(filename, delay=0.9)
            except Exception as e:
                print(f"  ⚠ Could not capture {filename}: {e}")

        # 5. Calibration wizard
        page.goto(BASE_URL, wait_until="networkidle")
        for sel in ["#calibrationBtn", "[onclick*='calibr']", "button.calibrate-btn"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    time.sleep(0.7)
                    break
            except:
                pass
        shot("calibration_wizard.png")
        page.keyboard.press("Escape")

        # 6. Nav bar screenshot
        page.goto(BASE_URL, wait_until="networkidle")
        nav = page.locator(".module-nav, #moduleNav, nav.tabs").first
        try:
            nav.screenshot(path=os.path.join(OUT_DIR, "nav_bar.png"))
            print("  ✅ nav_bar.png")
        except:
            shot("nav_bar.png")

        browser.close()
        return True

if not capture_via_playwright():
    print("⚠ Playwright not available. Trying to install...")
    ret = subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "--quiet"], capture_output=True)
    if ret.returncode == 0:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        print("Playwright installed. Please re-run this script.")
    else:
        print("❌ Could not install playwright.")
        print("Please run: pip install playwright && playwright install chromium")
        sys.exit(1)
