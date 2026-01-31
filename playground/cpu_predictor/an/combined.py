#!/usr/bin/env python3
import subprocess
import json
import csv
import time
from datetime import datetime
from pathlib import Path
import threading
from collections import deque

import psutil

# =========================
# CONFIG
# =========================
WINDOW = 60                      # WPM window seconds
INPUT_ACTIVE_WINDOW = 3.0        # active threshold
BURST_IDLE_THRESHOLD = 5.0
EMA_ALPHA = 0.3
INTERVAL = 1.0                   # log interval seconds

PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "combined_log.csv"

# =========================
# GLOBAL STATE (typing)
# =========================
keystrokes = deque()
last_keyboard_time = 0.0
last_mouse_time = 0.0
keys_counter = 0

typing_burst_start = None
focus_streak_start = None

last_window_id = None
window_switch_count = 0

prev_smooth_wpm = 0.0

# =========================
# SYSTEM IO STATE
# =========================
prev_disk = psutil.disk_io_counters()
prev_net = psutil.net_io_counters()

# =========================
# CSV INIT
# =========================
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp",
            "cpu_percent",
            "ram_percent",
            "disk_read_Bps",
            "disk_write_Bps",
            "net_in_Bps",
            "net_out_Bps",
            "window_id",
            "app_id",
            "pid",
            "process_count",
            "keyboard_active",
            "mouse_active",
            "true_focus",
            "avg_wpm",
            "instant_wpm",
            "keys_per_sec",
            "typing_burst_sec",
            "idle_time_sec",
            "focus_streak_sec",
            "window_switch_count",
            "wpm_delta",
            "hour",
        ])

# =========================
# INPUT LISTENER
# =========================
def input_listener():
    global last_keyboard_time, last_mouse_time, keys_counter

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
            if "pressed" in line:
                keystrokes.append(now)
                keys_counter += 1
                while keystrokes and now - keystrokes[0] > WINDOW:
                    keystrokes.popleft()

        elif "POINTER_MOTION" in line or "BUTTON_" in line:
            last_mouse_time = now

# =========================
# INPUT STATE HELPERS
# =========================
def is_keyboard_active():
    return time.time() - last_keyboard_time <= INPUT_ACTIVE_WINDOW

def is_mouse_active():
    return time.time() - last_mouse_time <= INPUT_ACTIVE_WINDOW

def get_idle_time():
    return round(time.time() - max(last_keyboard_time, last_mouse_time), 1)

# =========================
# TYPING METRICS
# =========================
def avg_wpm():
    return round(len(keystrokes) / 5, 1)

def get_keys_per_sec():
    global keys_counter
    k = keys_counter
    keys_counter = 0
    return k

def instant_wpm(keys_per_sec):
    return round((keys_per_sec * 60) / 5, 1)

def get_typing_burst():
    global typing_burst_start
    idle = get_idle_time()

    if idle < BURST_IDLE_THRESHOLD:
        if typing_burst_start is None:
            typing_burst_start = time.time()
        return round(time.time() - typing_burst_start, 1)
    else:
        typing_burst_start = None
        return 0.0

def get_focus_streak():
    global focus_streak_start

    if is_keyboard_active() or is_mouse_active():
        if focus_streak_start is None:
            focus_streak_start = time.time()
        return round(time.time() - focus_streak_start, 1)
    else:
        focus_streak_start = None
        return 0.0

# =========================
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
            if p.name.isdigit():
                try:
                    if (p / "exe").resolve() == target_exe:
                        count += 1
                except Exception:
                    pass
        return count
    except Exception:
        return 0

# =========================
# SYSTEM METRICS
# =========================
def get_system_metrics():
    global prev_disk, prev_net

    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    disk = psutil.disk_io_counters()
    disk_read = int((disk.read_bytes - prev_disk.read_bytes) / INTERVAL)
    disk_write = int((disk.write_bytes - prev_disk.write_bytes) / INTERVAL)
    prev_disk = disk

    net = psutil.net_io_counters()
    net_in = int((net.bytes_recv - prev_net.bytes_recv) / INTERVAL)
    net_out = int((net.bytes_sent - prev_net.bytes_sent) / INTERVAL)
    prev_net = net

    return cpu, ram, disk_read, disk_write, net_in, net_out

# =========================
# MAIN LOGGER
# =========================
def log_row():
    global last_window_id, window_switch_count, prev_smooth_wpm

    # --- system stats ---
    cpu, ram, d_read, d_write, n_in, n_out = get_system_metrics()

    # --- window stats ---
    data = get_focused_window()
    if not data:
        return

    pid = data.get("pid")
    window_id = data.get("id")
    app_id = data.get("app_id")

    if last_window_id and window_id != last_window_id:
        window_switch_count += 1
    last_window_id = window_id

    keyboard = int(is_keyboard_active())
    mouse = int(is_mouse_active())
    true_focus = int(keyboard or mouse)

    keys_sec = get_keys_per_sec()
    avg = avg_wpm()
    inst = instant_wpm(keys_sec)

    smooth_wpm = EMA_ALPHA * avg + (1 - EMA_ALPHA) * prev_smooth_wpm
    wpm_delta = round(smooth_wpm - prev_smooth_wpm, 1)
    prev_smooth_wpm = smooth_wpm

    row = [
        datetime.now().isoformat(timespec="seconds"),
        cpu,
        ram,
        d_read,
        d_write,
        n_in,
        n_out,
        window_id,
        app_id,
        pid,
        get_process_count(pid),
        keyboard,
        mouse,
        true_focus,
        avg,
        inst,
        keys_sec,
        get_typing_burst(),
        get_idle_time(),
        get_focus_streak(),
        window_switch_count,
        wpm_delta,
        datetime.now().hour,
    ]

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=input_listener, daemon=True).start()

    while True:
        t0 = time.time()
        log_row()
        time.sleep(max(0, INTERVAL - (time.time() - t0)))
