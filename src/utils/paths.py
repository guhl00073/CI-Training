import sys
import os
import pathlib
import tempfile
import subprocess


def get_subprocess_flags() -> dict:
    """
    Returns platform-specific kwargs for subprocess execution.
    On Windows, sets creationflags=subprocess.CREATE_NO_WINDOW to prevent
    console windows from popping up when spawning child processes (e.g. powershell, ffmpeg, ffplay).
    """
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return {"creationflags": flags}
    return {}


def get_resource_path(relative_path: str = "") -> pathlib.Path:
    """
    Returns absolute path to a bundled read-only resource file.
    Supports both PyInstaller frozen applications (sys._MEIPASS) and local dev environment.
    """
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        base_path = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(sys.executable).parent)).resolve()
    else:
        # Running in dev mode: project root is 2 levels up from src/utils/
        base_path = pathlib.Path(__file__).parent.parent.parent.resolve()

    if relative_path:
        return base_path / relative_path
    return base_path


def get_user_data_dir(app_name: str = "CI-Hörtrainer") -> pathlib.Path:
    """
    Returns standard OS user application data directory:
      - macOS: ~/Library/Application Support/CI-Hörtrainer
      - Windows: %APPDATA%/CI-Hörtrainer
      - Linux: ~/.local/share/CI-Hörtrainer
    Falls back gracefully to tempdir if permissions are restricted (e.g. sandboxed test runner).
    """
    # Use temp directory during automated unit test runs
    if os.environ.get("CI_TESTING") or "unittest" in sys.modules or "pytest" in sys.modules:
        path = pathlib.Path(tempfile.gettempdir()) / app_name
    else:
        home = pathlib.Path.home()
        if sys.platform == "darwin":
            path = home / "Library" / "Application Support" / app_name
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                path = pathlib.Path(appdata) / app_name
            else:
                path = home / "AppData" / "Roaming" / app_name
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            if xdg:
                path = pathlib.Path(xdg) / app_name
            else:
                path = home / ".local" / "share" / app_name

    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        path = pathlib.Path(tempfile.gettempdir()) / app_name
        path.mkdir(parents=True, exist_ok=True)

    return path


def get_db_path() -> pathlib.Path:
    """
    Returns the absolute path for the SQLite user progress database.
    Located in standard user data directory so it persists across app updates.
    """
    return get_user_data_dir() / "ci-training.db"
