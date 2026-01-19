#!/usr/bin/env python3
import subprocess
import json
import csv
import time
from datetime import datetime
from pathlib import Path
import threading
import psutil

# =========================
# CONFIG
# =========================
PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "unified_log.csv"
INTERVAL_SEC = 1.0

# =========================
# CSV INIT
# =========================
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp",

            # --- System metrics (targets) ---
            "cpu_percent",
            "ram_percent",
            "disk_read_bytes",
            "disk_write_bytes",
            "net_bytes_recv",
            "net_bytes_sent",

            # --- Active window context ---
            "active_window_id",
            "active_app_id",
            "active_pid",
            "active_process_count",

            # --- Global system state ---
            "total_process_count",

            # --- User behavior ---
            "keyboard_rate",
            "mouse_rate",
        ])

# =========================
# INPUT COUNTERS (GLOBAL)
# =========================
keyboard_counter = 0
mouse_counter = 0
prev_keyboard = 0
prev_mouse = 0

# =========================
# DISK / NET PREV
# =========================
prev_disk = psutil.disk_io_counters()
prev_net = psutil.net_io_counters()

# =========================
# LIBINPUT LISTENER
# =========================
def input_listener():
    global keyboard_counter, mouse_counter

    proc = subprocess.Popen(
        ["libinput", "debug-events"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        if "KEYBOARD_KEY" in line:
            keyboard_counter += 1
        elif "POINTER_MOTION" in line or "BUTTON_" in line:
            mouse_counter += 1

# =========================
# FOCUSED WINDOW (NIRI)
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
# PROCESS COUNT BY EXEC
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
# MAIN LOGGING LOOP
# =========================
def log_once():
    global prev_keyboard, prev_mouse, prev_disk, prev_net

    # -------- System metrics --------
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent

    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    disk_read = disk.read_bytes - prev_disk.read_bytes
    disk_write = disk.write_bytes - prev_disk.write_bytes
    net_recv = net.bytes_recv - prev_net.bytes_recv
    net_sent = net.bytes_sent - prev_net.bytes_sent

    prev_disk = disk
    prev_net = net

    total_process_count = len(psutil.pids())

    # -------- Keyboard / mouse rate --------
    kb_now = keyboard_counter
    ms_now = mouse_counter

    keyboard_rate = kb_now - prev_keyboard
    mouse_rate = ms_now - prev_mouse

    prev_keyboard = kb_now
    prev_mouse = ms_now

    # -------- Focused window --------
    win = get_focused_window() or {}

    pid = win.get("pid")
    active_process_count = get_process_count(pid) if pid else 0

    row = [
        datetime.now().isoformat(timespec="seconds"),

        cpu,
        ram,
        disk_read,
        disk_write,
        net_recv,
        net_sent,

        win.get("id"),
        win.get("app_id"),
        pid,
        active_process_count,

        total_process_count,

        keyboard_rate,
        mouse_rate,
    ]

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    psutil.cpu_percent(interval=None)  # warmup

    threading.Thread(target=input_listener, daemon=True).start()

    while True:
        start = time.time()
        log_once()

        elapsed = time.time() - start
        if elapsed < INTERVAL_SEC:
            time.sleep(INTERVAL_SEC - elapsed)
