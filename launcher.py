from pathlib import Path
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def choose_port(start=8501, end=8510):
    for port in range(start, end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            pass
        finally:
            sock.close()
    raise RuntimeError("No free local port was found between 8501 and 8510.")


def port_is_ready(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def find_chrome_exe() -> str | None:
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), r"Google\Chrome\Application\chrome.exe"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    for cmd in ["chrome.exe", "chrome"]:
        found = shutil.which(cmd)
        if found:
            return found

    return None


def open_browser(url: str):
    chrome = find_chrome_exe()

    if chrome:
        try:
            subprocess.Popen([chrome, "--new-window", url], close_fds=True)
            print("Opened in Google Chrome.")
            return
        except Exception:
            pass

    # Fallback: open the default browser if Chrome is not available.
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            print("Chrome was not found. Opened in the default browser instead.")
            return
        except Exception:
            pass

    webbrowser.open(url)
    print("Chrome was not found. Opened in the default browser instead.")


def wait_for_server_then_open(port: int):
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 120

    while time.time() < deadline:
        if port_is_ready(port):
            print()
            print("Server is ready.")
            print(f"Opening: {url}")
            print()
            open_browser(url)
            return
        time.sleep(0.5)

    print()
    print("Server did not become reachable within 120 seconds.")
    print(f"Try opening manually: {url}")
    print()


def write_error_log(text: str) -> Path:
    target = executable_dir() / "PreyEnergyCalculator_error.txt"
    try:
        target.write_text(text, encoding="utf-8")
        return target
    except Exception:
        fallback = Path(os.environ.get("TEMP", ".")) / "PreyEnergyCalculator_error.txt"
        fallback.write_text(text, encoding="utf-8")
        return fallback


def main():
    base = resource_dir()
    os.chdir(base)

    # PyInstaller changes Streamlit's module path so Streamlit may infer
    # developmentMode=True. Force production mode before Streamlit config
    # is parsed; otherwise server.port conflicts with development mode.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    port = choose_port()
    url = f"http://127.0.0.1:{port}"

    print("=" * 62)
    print("Prey Energy Contribution Calculator")
    print("=" * 62)
    print(f"Starting local server on port {port}...")
    print(f"Browser URL: {url}")
    print("Please keep this window open while using the program.")
    print()

    threading.Thread(
        target=wait_for_server_then_open,
        args=(port,),
        daemon=True,
    ).start()

    # Import only after the console banner is visible so startup failures
    # are captured by the outer exception handler.
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(base / "app.py"),
        "--global.developmentMode",
        "false",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.fileWatcherType=none",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    return stcli.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Program stopped by user.")
    except BaseException:
        details = traceback.format_exc()
        log_path = write_error_log(details)

        print()
        print("=" * 62)
        print("STARTUP ERROR")
        print("=" * 62)
        print(details)
        print()
        print(f"Error log saved to: {log_path}")
        print()
        print("This window will stay open so the error can be reviewed.")
        try:
            input("Press Enter to close...")
        except Exception:
            time.sleep(30)
