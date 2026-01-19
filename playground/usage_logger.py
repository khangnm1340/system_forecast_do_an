#!/usr/bin/env python3
import psutil
import time
import csv
import subprocess
import json
import threading
from evdev import InputDevice, list_devices, ecodes

LOGFILE = "system_usage.csv"
INTERVAL = 1.0   # seconds


# ---------- Input event counters ----------
keyboard_events = 0
mouse_events = 0

def find_devices():
    keyboards = []
    mice = []
    for path in list_devices():
        dev = InputDevice(path)
        caps = dev.capabilities()
        if ecodes.EV_KEY in caps:
            keyboards.append(dev)
        if ecodes.EV_REL in caps or ecodes.EV_ABS in caps:
            mice.append(dev)
    return keyboards, mice

def input_counter(dev, is_keyboard=True):
    global keyboard_events, mouse_events
    for event in dev.read_loop():
        if event.type in (ecodes.EV_KEY, ecodes.EV_REL, ecodes.EV_ABS):
            if is_keyboard:
                keyboard_events += 1
            else:
                mouse_events += 1

def start_input_threads():
    keyboards, mice = find_devices()
    for k in keyboards:
        t = threading.Thread(target=input_counter, args=(k, True), daemon=True)
        t.start()
    for m in mice:
        t = threading.Thread(target=input_counter, args=(m, False), daemon=True)
        t.start()


# ---------- Niri window info ----------
def get_niri_info():
    try:
        out = subprocess.check_output(["niri", "msg", "-j"], text=True)
        data = json.loads(out)
        windows = data["windows"]
        focused = data["focused"]
        active_class = ""

        for w in windows:
            if w["id"] == focused:
                active_class = w.get("app_id", "")
                break

        return active_class, len(windows)

    except Exception:
        return "", 0


# ---------- Main logger ----------
def main():
    start_input_threads()

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
