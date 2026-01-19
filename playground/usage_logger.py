#!/usr/bin/env python3
import psutil
import time
import csv
import subprocess
import json
import threading

LOGFILE = "system_usage.csv"
INTERVAL = 1.0   # seconds


# ---------- Input event counters ----------
keyboard_events = 0
mouse_events = 0

def libinput_monitor():
    global keyboard_events, mouse_events

    proc = subprocess.Popen(
        ["libinput", "debug-events", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type", "")

        if etype == "KEYBOARD_KEY":
            keyboard_events += 1

        elif etype in ("POINTER_MOTION", "POINTER_BUTTON"):
            mouse_events += 1


def start_input_thread():
    t = threading.Thread(target=libinput_monitor, daemon=True)
    t.start()


# ---------- Niri window info ----------
def get_niri_info():
    try:
        # Get focused window
        out = subprocess.check_output(["niri", "msg", "-j", "focused-window"], text=True)
        focused = json.loads(out)
        active_class = focused.get("app_id", "")

        # Get total window count
        out2 = subprocess.check_output(["niri", "msg", "-j", "windows"], text=True)
        windows = json.loads(out2)
        win_count = len(windows)

        return active_class, win_count

    except Exception:
        return "", 0


# ---------- Main logger ----------
def main():
    start_input_thread()

    prev_disk = psutil.disk_io_counters()
    prev_net = psutil.net_io_counters()

    with open(LOGFILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "cpu_percent",
            "ram_percent",
            "disk_read_Bps",
            "disk_write_Bps",
            "net_in_Bps",
            "net_out_Bps",
            "active_window_class",
            "window_count",
            "keyboard_rate",
            "mouse_rate",
            "process_count"
        ])

        global keyboard_events, mouse_events

        while True:
            t0 = time.time()

            # CPU & RAM
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent

            # Disk IO
            disk = psutil.disk_io_counters()
            disk_read = (disk.read_bytes - prev_disk.read_bytes) / INTERVAL
            disk_write = (disk.write_bytes - prev_disk.write_bytes) / INTERVAL
            prev_disk = disk

            # Net IO
            net = psutil.net_io_counters()
            net_in = (net.bytes_recv - prev_net.bytes_recv) / INTERVAL
            net_out = (net.bytes_sent - prev_net.bytes_sent) / INTERVAL
            prev_net = net

            # Processes
            proc_count = len(psutil.pids())

            # Windows (niri)
            active_class, win_count = get_niri_info()

            # Input rates
            k_rate = keyboard_events / INTERVAL
            m_rate = mouse_events / INTERVAL
            keyboard_events = 0
            mouse_events = 0

            writer.writerow([
                int(t0),
                cpu,
                ram,
                int(disk_read),
                int(disk_write),
                int(net_in),
                int(net_out),
                active_class,
                win_count,
                int(k_rate),
                int(m_rate),
                proc_count
            ])

            f.flush()

            time.sleep(max(0, INTERVAL - (time.time() - t0)))


if __name__ == "__main__":
    main()
