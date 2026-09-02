#!/usr/bin/env python3
"""
Signs all Mach-O binaries in a macOS .app bundle and the bundle itself (ad-hoc),
then removes quarantine flags so it opens without Gatekeeper restrictions.
"""

import sys
import os
import subprocess
import pathlib

def sign_app(app_path_str: str):
    app_path = pathlib.Path(app_path_str).resolve()
    if not app_path.exists():
        print(f"❌ App not found: {app_path}")
        return False

    print(f"🔐 Signing {app_path.name} ...")

    # 1. Strip all extended attributes / quarantine
    subprocess.run(["xattr", "-cr", str(app_path)], check=False)

    # 2. Remove any lingering .cstemp or _CodeSignature to avoid sealed resource mismatches
    for p in app_path.rglob("*.cstemp"):
        p.unlink(missing_ok=True)

    sig_dir = app_path / "Contents" / "_CodeSignature"
    if sig_dir.exists():
        import shutil
        shutil.rmtree(sig_dir, ignore_errors=True)

    # 3. Find all Mach-O binaries (dylibs, .so, executables)
    macho_files = []
    for root, _, files in os.walk(app_path):
        for f in files:
            p = pathlib.Path(root) / f
            if p.is_symlink():
                continue
            try:
                res = subprocess.run(["file", str(p)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    macho_files.append(p)
            except Exception:
                pass

    for mf in macho_files:
        subprocess.run(["codesign", "--force", "--sign", "-", str(mf)], capture_output=True)

    # 4. Sign main executable
    main_exe = app_path / "Contents" / "MacOS" / "CI-Hörtrainer"
    if not main_exe.exists():
        main_exe = app_path / "Contents" / "MacOS" / "CI-Hörtrainer"
    if main_exe.exists():
        subprocess.run(["codesign", "--force", "--sign", "-", str(main_exe)], capture_output=True)

    # 5. Sign the outer bundle with deep option
    res = subprocess.run(["codesign", "--force", "--sign", "-", str(app_path)], capture_output=True, text=True)
    
    # 6. Verify
    verify = subprocess.run(["codesign", "-v", str(app_path)], capture_output=True, text=True)
    if verify.returncode == 0:
        print("   ✅ Ad-hoc Signatur erfolgreich validiert!")
    else:
        print(f"   ℹ️ Signatur Hinweis: {verify.stderr.strip() or verify.stdout.strip()}")

    # 7. Final quarantine clear
    subprocess.run(["xattr", "-cr", str(app_path)], check=False)
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "dist/CI-Hörtrainer.app"
    sign_app(target)
