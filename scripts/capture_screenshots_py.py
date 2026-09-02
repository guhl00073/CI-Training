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
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="domcontentloaded")
        
        # 1. Dashboard (with active exercise)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        try:
            # Open Minimal Pairs tab for an active exercise state on dashboard
            page.locator(".tab-btn[data-tab='mp']").first.click(timeout=2000)
            time.sleep(0.5)
            page.locator("#mpPlayBtn").first.click(timeout=1000)
            time.sleep(0.5)
        except: pass
        shot("dashboard.png", delay=1.5)

        # 2. Audio Settings Panel
        try:
            # Collapse training menu so audio settings is in focus
            page.evaluate("document.getElementById('navTabsDetails').open = false")
            page.evaluate("document.getElementById('controlPanelDetails').open = true")
        except: pass
        shot("audio_settings.png", delay=1.0)
        
        # Restore state for subsequent screenshots
        try:
            page.evaluate("document.getElementById('navTabsDetails').open = true")
            page.evaluate("document.getElementById('controlPanelDetails').open = false")
        except: pass

        # Voice dropdown
        # (Native dropdowns cannot be captured open by playwright.
        # voice_selection.png must be created manually and kept in git.)

        # 3. Profile modal
        page.goto(BASE_URL, wait_until="domcontentloaded")
        for sel in ["#openProfileBtn"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click(force=True, timeout=2000)
                    time.sleep(0.7)
                    break
            except:
                pass
        shot("profiles.png")
        page.keyboard.press("Escape")
        time.sleep(0.4)

        # 3.5. Therapist Report modal
        page.goto(BASE_URL, wait_until="domcontentloaded")
        for sel in ["#openTherapistReportBtn", "button[onclick*='openTherapistReport']"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click(force=True, timeout=2000)
                    time.sleep(1.0)
                    break
            except:
                pass
        shot("therapist_report.png")
        page.keyboard.press("Escape")
        time.sleep(0.4)

        # 4. Module tabs
        tabs = [
            ("mp",        "module_minimal_pairs.png", "#mpPlayBtn"),
            ("es",        "module_einsilber.png", "#esPlayBtn"),
            ("ms",        "module_mehrsilber.png", "#msPlayBtn"),
            ("num",       "module_zahlen.png", "#numPlayBtn"),
            ("sent",      "module_saetze.png", "#sentPlayBtn"),
            ("olsa",      "module_olsa.png", "#olsaStartTestBtn"),
            ("noise",     "module_stoerschall.png", "#noisePlayBtn"),
            ("memory",    "module_gedaechtnis.png", "#memoryPlayBtn"),
            ("weakness",  "module_schwachstellen.png", "#weaknessPlayBtn"),
            ("audiogram", "module_audiogramm.png", None),
            ("stats",     "module_statistik.png", None),
            ("editor",    "module_editor.png", None),
        ]
        for tab_info in tabs:
            tab_id = tab_info[0]
            filename = tab_info[1]
            start_btn = tab_info[2] if len(tab_info) > 2 else None
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded")
                time.sleep(0.5)
                clicked = False
                for sel in [f"[data-tab='{tab_id}']", f"#nav-{tab_id}", f".tab-btn[data-tab='{tab_id}']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible():
                            el.click(force=True, timeout=2000)
                            clicked = True
                            break
                    except:
                        pass
                if not clicked:
                    # Try JS eval
                    page.evaluate(f"document.querySelector('[data-tab=\"{tab_id}\"]')?.click()")
                
                # Editor might not render data if it was inactive when loaded
                if tab_id == "editor":
                    try:
                        page.evaluate("if(typeof renderEditorList === 'function') renderEditorList()")
                        time.sleep(1.0)
                    except: pass

                time.sleep(0.4)
                if start_btn:
                    try:
                        page.locator(start_btn).first.click(timeout=1000)
                        time.sleep(0.8)
                    except: pass
                
                shot(filename, delay=0.9)
            except Exception as e:
                print(f"  ⚠ Could not capture {filename}: {e}")

        # 3.4. Calibration wizard (preserved from manual upload)
        print("  ✅ calibration_wizard.png (preserved)")


        # 6. Nav bar screenshot
        page.goto(BASE_URL, wait_until="domcontentloaded")
        time.sleep(0.5)
        nav = page.locator(".nav-tabs").first
        try:
            nav.screenshot(path=os.path.join(OUT_DIR, "nav_bar.png"))
            print("  ✅ nav_bar.png")
        except Exception as e:
            print("  ⚠ Could not capture nav_bar.png:", e)

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
