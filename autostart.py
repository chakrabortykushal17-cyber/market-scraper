"""
Windows Auto-Start Manager for Finance Intel Market Scraper.
Configures automatic startup of the scraper on PC boot/logon via Windows Startup folder.
Uses a VBScript launcher to run headlessly in the background without popping up CMD windows.
"""

import os
import sys
import argparse

STARTUP_FILE_NAME = "FinanceIntel_Scraper_Startup.vbs"


def get_startup_dir():
    """Returns the Windows Startup folder path for the current user."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser(r"~\AppData\Roaming")
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")


def get_startup_file_path():
    return os.path.join(get_startup_dir(), STARTUP_FILE_NAME)


def is_autostart_enabled():
    """Checks if the startup VBS script exists in the Windows Startup folder."""
    return os.path.isfile(get_startup_file_path())


def enable_autostart(target="scraper"):
    """
    Creates a VBScript launcher in the Windows Startup folder to silently run python on startup.
    target options:
      - 'scraper': runs run_scraper.py
      - 'app': runs app.py
      - 'both': runs both run_scraper.py and app.py
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    # Replace python.exe with pythonw.exe if available for completely windowless execution
    pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    if os.path.isfile(pythonw_exe):
        exe_path = pythonw_exe
    else:
        exe_path = python_exe

    startup_path = get_startup_file_path()
    lines = [
        'Set WshShell = CreateObject("WScript.Shell")',
        f'WshShell.CurrentDirectory = "{base_dir}"'
    ]

    if target in ["scraper", "both"]:
        scraper_script = os.path.join(base_dir, "run_scraper.py")
        lines.append(f'WshShell.Run """{exe_path}"" ""{scraper_script}""", 0, False')

    if target in ["app", "both"]:
        app_script = os.path.join(base_dir, "app.py")
        lines.append(f'WshShell.Run """{exe_path}"" ""{app_script}""", 0, False')

    vbs_content = "\r\n".join(lines) + "\r\n"

    try:
        os.makedirs(os.path.dirname(startup_path), exist_ok=True)
        with open(startup_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        return True, f"Auto-start enabled successfully! Script created at: {startup_path}"
    except Exception as e:
        return False, f"Failed to enable auto-start: {str(e)}"


def disable_autostart():
    """Removes the VBScript launcher from the Windows Startup folder."""
    startup_path = get_startup_file_path()
    if os.path.isfile(startup_path):
        try:
            os.remove(startup_path)
            return True, "Auto-start disabled successfully! Startup script removed."
        except Exception as e:
            return False, f"Failed to disable auto-start: {str(e)}"
    return True, "Auto-start is already disabled."


def get_status_summary():
    """Returns a dictionary summary of auto-start status."""
    enabled = is_autostart_enabled()
    startup_path = get_startup_file_path()
    return {
        "enabled": enabled,
        "startup_path": startup_path,
        "exists": os.path.isfile(startup_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Manage PC Auto-Start for Finance Intel Scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Enable auto-start on PC boot")
    group.add_argument("--disable", action="store_true", help="Disable auto-start on PC boot")
    group.add_argument("--status", action="store_true", help="Check auto-start status")

    parser.add_argument(
        "--target",
        choices=["scraper", "app", "both"],
        default="scraper",
        help="Target process to launch on startup (default: scraper)",
    )

    args = parser.parse_args()

    if args.enable:
        success, msg = enable_autostart(target=args.target)
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg}")
    elif args.disable:
        success, msg = disable_autostart()
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg}")
    elif args.status:
        status = get_status_summary()
        print("=" * 50)
        print("  Finance Intel — Auto-Start Status")
        print("=" * 50)
        print(f"  Enabled:      {'YES (Active on boot)' if status['enabled'] else 'NO (Disabled)'}")
        print(f"  Startup File: {status['startup_path']}")
        print("=" * 50)


if __name__ == "__main__":
    main()
