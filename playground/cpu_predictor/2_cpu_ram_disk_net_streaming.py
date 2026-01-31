#!/usr/bin/env python3
import csv
import time
from pathlib import Path

import psutil

# =========================
# CONFIG
# =========================
INTERVAL = 1.0

PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "system_metrics.csv"

# =========================
# INITIAL STATE
# =========================
prev_disk = psutil.disk_io_counters()
prev_net = psutil.net_io_counters()

# =========================
# CSV INIT
# =========================
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "cpu_percent",
            "ram_percent",
            "disk_read_Bps",
            "disk_write_Bps",
            "net_in_Bps",
            "net_out_Bps",
        ])

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
# MAIN LOOP
# =========================
if __name__ == "__main__":
    while True:
        t0 = time.time()

        cpu, ram, d_read, d_write, n_in, n_out = get_system_metrics()

        row = [
            cpu,
            ram,
            d_read,
            d_write,
            n_in,
            n_out,
        ]

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

        time.sleep(max(0, INTERVAL - (time.time() - t0)))
