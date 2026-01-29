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
INTERVAL = 1.0                   # log interval seconds
WINDOW = 60                      # WPM window seconds
INPUT_ACTIVE_WINDOW = 3.0        # active threshold
PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "comprehensive_activity_log.csv"

# =========================
# GLOBAL STATE
# =========================
keystrokes = deque()
last_keyboard_time = 0.0
last_mouse_time = 0.0
keys_counter = 0

# GPU State
latest_gpu_data = {}
gpu_headers = []

# System IO State
prev_disk = psutil.disk_io_counters()
prev_net = psutil.net_io_counters()

# =========================
# GPU MONITOR THREAD
# =========================
def gpu_listener():
    """Reads intel_gpu_top -c continuously and updates global state."""
    global latest_gpu_data, gpu_headers
    
    # -c outputs CSV format
    # -s 1000 samples every 1000ms
    proc = subprocess.Popen(
        ["intel_gpu_top", "-c", "-s", "1000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(',')
        
        # Detect header row
        if "Freq MHz req" in line:
            gpu_headers = [f"gpu_{p.strip().replace(' ', '_').replace('%', 'pct')}" for p in parts]
            continue
        
        # Parse data row
        if gpu_headers and len(parts) == len(gpu_headers):
            try:
                temp_dict = {}
                for i, val in enumerate(parts):
                    temp_dict[gpu_headers[i]] = float(val)
                latest_gpu_data = temp_dict
            except ValueError:
                pass

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
# HELPERS
# =========================
def get_focused_window():
    try:
        # Optimized for Niri
        result = subprocess.run(
            ["niri", "msg", "-j", "focused-window"],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except:
        return None

def get_keys_per_sec():
    global keys_counter
    k = keys_counter
    keys_counter = 0
    return k

def get_idle_time():
    return round(time.time() - max(last_keyboard_time, last_mouse_time), 1)

# =========================
# MAIN LOGGER
# =========================
def log_row():
    global prev_disk, prev_net

    # 1. System Metrics
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    now_disk = psutil.disk_io_counters()
    d_read = int((now_disk.read_bytes - prev_disk.read_bytes) / INTERVAL)
    d_write = int((now_disk.write_bytes - prev_disk.write_bytes) / INTERVAL)
    prev_disk = now_disk

    now_net = psutil.net_io_counters()
    n_in = int((now_net.bytes_recv - prev_net.bytes_recv) / INTERVAL)
    n_out = int((now_net.bytes_sent - prev_net.bytes_sent) / INTERVAL)
    prev_net = now_net

    # 2. App/Window Metrics
    win_data = get_focused_window()
    app_id = win_data.get("app_id", "unknown") if win_data else "none"
    win_title = win_data.get("title", "none") if win_data else "none"

    # 3. Input Metrics
    k_active = int(time.time() - last_keyboard_time <= INPUT_ACTIVE_WINDOW)
    m_active = int(time.time() - last_mouse_time <= INPUT_ACTIVE_WINDOW)
    kps = get_keys_per_sec()
    idle = get_idle_time()

    # 4. GPU Metrics
    gpu_row_data = []
    max_gpu_val = 0.0
    
    if gpu_headers:
        # Calculate Max of engines (RCS, BCS, VCS, VECS)
        # Note: Mapping names based on intel_gpu_top output
        engine_keys = ["gpu_RCS_pct", "gpu_BCS_pct", "gpu_VCS_pct", "gpu_VECS_pct"]
        engine_vals = [latest_gpu_data.get(k, 0.0) for k in engine_keys]
        max_gpu_val = max(engine_vals) if engine_vals else 0.0
        
        # Prepare all GPU columns in order
        for h in gpu_headers:
            gpu_row_data.append(latest_gpu_data.get(h, 0.0))
    else:
        # If GPU thread hasn't started yet, fill with 0
        gpu_row_data = [0.0] * 18 

    # 5. Build Final Row
    # Order: timestamp, cpu, ram, disk_r, disk_w, net_i, net_o, app_id, title, k_act, m_act, kps, idle, max_gpu, [all gpu stats]
    row = [
        datetime.now().isoformat(timespec="seconds"),
        cpu, ram, d_read, d_write, n_in, n_out,
        app_id, win_title,
        k_active, m_active, kps, idle,
        max_gpu_val
    ] + gpu_row_data

    # 6. CSV Header Init (Dynamic based on GPU headers)
    if not CSV_PATH.exists():
        base_headers = [
            "timestamp", "cpu_percent", "ram_percent", "disk_read_Bps", "disk_write_Bps",
            "net_in_Bps", "net_out_Bps", "app_id", "window_title",
            "keyboard_active", "mouse_active", "keys_per_sec", "idle_time_sec", "max_gpu"
        ]
        full_headers = base_headers + (gpu_headers if gpu_headers else ["gpu_data_pending"])
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(full_headers)

    # 7. Write Data
    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow(row)

# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":
    print(f"Logging started. Saving to {CSV_PATH}")
    
    # Start Background Threads
    threading.Thread(target=input_listener, daemon=True).start()
    threading.Thread(target=gpu_listener, daemon=True).start()

    # Wait a moment for GPU headers to populate
    time.sleep(1.5)

    try:
        while True:
            t0 = time.time()
            log_row()
            # Precise sleep to maintain INTERVAL
            elapsed = time.time() - t0
            time.sleep(max(0, INTERVAL - elapsed))
    except KeyboardInterrupt:
        print("\nLogging stopped.")
