#!/usr/bin/env python3
import subprocess
import psutil
import time
import csv
from threading import Thread

# --- CONFIG ---
DURATION_SEC = 30
INTERVAL_SEC = 1
KEYBOARD_DEVICE = "/dev/input/event11"   # kanata keyboard (or event0)
MOUSE_DEVICE = "/dev/input/event9"       # touchpad
CSV_FILE = "metrics_log.csv"

# --- Helpers ---
def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore").strip()
    except subprocess.CalledProcessError:
        return ""

def get_mango_info():
    text = run_cmd("mmsg -g -c")
    title = ""
    appid = ""
    for line in text.splitlines():
        if line.startswith("title:"):
            title = line.split(":",1)[1].strip()
        if line.startswith("app_id:"):
            appid = line.split(":",1)[1].strip()
    return title, appid

# --- Persistent libinput readers ---
def event_reader(device, counter):
    """
    Runs forever, counting libinput events from a device.
    """
    proc = subprocess.Popen(
        ["libinput", "debug-events", "--device", device],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        if line.strip():
            counter[0] += 1

# --- MAIN ---
def main():
    # Warm up cpu_percent
    psutil.cpu_percent(interval=None)

    # Shared counters
    keyboard_counter = [0]
    mouse_counter = [0]

    # Start background readers
    Thread(target=event_reader, args=(KEYBOARD_DEVICE, keyboard_counter), daemon=True).start()
    Thread(target=event_reader, args=(MOUSE_DEVICE, mouse_counter), daemon=True).start()

    # Initial disk/net values for rate calculation
    prev_disk = psutil.disk_io_counters()
    prev_net = psutil.net_io_counters()
    prev_kb = keyboard_counter[0]
    prev_ms = mouse_counter[0]

    with open(CSV_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp",
            "cpu_percent",
            "ram_percent",
            "disk_read_bytes",
            "disk_write_bytes",
            "net_bytes_recv",
            "net_bytes_sent",
            "process_count",
            "active_title",
            "active_appid",
            "keyboard_rate",
            "mouse_rate",
        ])

        start_time = time.time()
        while time.time() - start_time < DURATION_SEC:
            loop_start = time.time()

            # --- System metrics ---
            cpu = psutil.cpu_percent(interval=0.0)
            ram = psutil.virtual_memory().percent
            di = psutil.disk_io_counters()
            ni = psutil.net_io_counters()
            pc = len(psutil.pids())

            # --- Rates ---
            disk_read = di.read_bytes - prev_disk.read_bytes
            disk_write = di.write_bytes - prev_disk.write_bytes
            net_recv = ni.bytes_recv - prev_net.bytes_recv
            net_sent = ni.bytes_sent - prev_net.bytes_sent

            prev_disk = di
            prev_net = ni

            # --- Keyboard / mouse rate ---
            kb_now = keyboard_counter[0]
            ms_now = mouse_counter[0]
            kb_rate = (kb_now - prev_kb) / INTERVAL_SEC
            ms_rate = (ms_now - prev_ms) / INTERVAL_SEC
            prev_kb = kb_now
            prev_ms = ms_now

            # --- Mango focused window ---
            title, appid = get_mango_info()

            # --- Write CSV ---
            w.writerow([
                round(time.time(), 3),
                cpu,
                ram,
                disk_read,
                disk_write,
                net_recv,
                net_sent,
                pc,
                title,
                appid,
                round(kb_rate, 2),
                round(ms_rate, 2),
            ])

            f.flush()

            # --- Sleep until next interval ---
            elapsed = time.time() - loop_start
            if elapsed < INTERVAL_SEC:
                time.sleep(INTERVAL_SEC - elapsed)

    print("Done. CSV saved to:", CSV_FILE)

if __name__ == "__main__":
    main()
