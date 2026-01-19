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
INTERVAL_SEC = 1.0  # 1 giây log 1 lần  <-- MODIFIED (đổi ý nghĩa)

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
            "keyboard_rate",     # <-- MODIFIED (đổi từ keyboard_active)
            "mouse_rate",        # <-- MODIFIED (đổi từ mouse_active)
        ])

# =========================
# INPUT STATE (GLOBAL)
# =========================
last_keyboard_time = 0.0
keyboard_counter = 0          # <-- MODIFIED (thêm bộ đếm)
mouse_counter = 0             # <-- MODIFIED (thêm bộ đếm)

prev_keyboard = 0              # <-- MODIFIED (lưu trạng thái trước)
prev_mouse = 0                 # <-- MODIFIED

# =========================
# INPUT LISTENER
# =========================
def input_listener():
    global last_keyboard_time, keyboard_counter, mouse_counter  # <-- MODIFIED

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
            keyboard_counter += 1          # <-- MODIFIED (đếm event)
        elif "POINTER_MOTION" in line or "BUTTON_" in line:
            mouse_counter += 1              # <-- MODIFIED (đếm event)

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
    global prev_keyboard, prev_mouse     # <-- MODIFIED

    data = get_focused_window()
    if not data:
        return

    pid = data.get("pid")
    if not pid:
        return

    # ===== TÍNH RATE THAY VÌ 0/1 =====
    kb_now = keyboard_counter             # <-- MODIFIED
    ms_now = mouse_counter                # <-- MODIFIED

    keyboard_rate = kb_now - prev_keyboard  # <-- MODIFIED
    mouse_rate = ms_now - prev_mouse        # <-- MODIFIED

    prev_keyboard = kb_now                  # <-- MODIFIED
    prev_mouse = ms_now                     # <-- MODIFIED

    row = [
        datetime.now().isoformat(timespec="seconds"),
        data.get("id"),
        data.get("app_id"),
        pid,
        get_process_count(pid),
        keyboard_rate,     # <-- MODIFIED
        mouse_rate,        # <-- MODIFIED
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
        time.sleep(INTERVAL_SEC)   # <-- MODIFIED (đúng nhịp 1Hz)
