import subprocess
import json
import csv
import time
from datetime import datetime
from pathlib import Path
import threading

# =========================
# CONFIG
# =========================
PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "active_window_log.csv"
INPUT_ACTIVE_WINDOW = 3.0  # giây

# =========================
# CSV INIT
# =========================
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp",
            "window_id",
            "app_id",
            "pid",
            "process_count",
            "keyboard_active",
            "mouse_active",
            "true_focus",
        ])

# =========================
# INPUT STATE (GLOBAL)
# =========================
last_keyboard_time = 0.0
last_mouse_time = 0.0

# =========================
# INPUT LISTENER
# =========================
def input_listener():
    global last_keyboard_time, last_mouse_time

    proc = subprocess.Popen(
        ["libinput", "debug-events"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        now = time.time()
        if "KEYBOARD_KEY" in line:
            last_keyboard_time = now
        elif "POINTER_MOTION" in line or "BUTTON_" in line:
            last_mouse_time = now


def is_keyboard_active():
    return (time.time() - last_keyboard_time) <= INPUT_ACTIVE_WINDOW


def is_mouse_active():
    return (time.time() - last_mouse_time) <= INPUT_ACTIVE_WINDOW


# ========================
# NIRI WINDOW
# =========================
def get_focused_window():
    try:
        result = subprocess.run(
            ["niri", "msg", "-j", "focused-window"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception:
        return None


# =========================
# PROCESS COUNT
# =========================
def get_process_count(pid: int) -> int:
    try:
        target_exe = Path(f"/proc/{pid}/exe").resolve()
        count = 0

        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue
            try:
                if (p / "exe").resolve() == target_exe:
                    count += 1
            except Exception:
                continue

        return count
    except Exception:
        return 0


# =========================
# LOGGING
# =========================
def log_window():
    data = get_focused_window()
    if not data:
        return

    pid = data.get("pid")
    if not pid:
        return

    keyboard = int(is_keyboard_active())
    mouse = int(is_mouse_active())
    true_focus = int(keyboard or mouse)

    row = [
        datetime.now().isoformat(timespec="seconds"),
        data.get("id"),
        data.get("app_id"),
        pid,
        get_process_count(pid),
        keyboard,
        mouse,
        true_focus,
    ]

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=input_listener, daemon=True).start()

    while True:
        log_window()
        time.sleep(1.0)
