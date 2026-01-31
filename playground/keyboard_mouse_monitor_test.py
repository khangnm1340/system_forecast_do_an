#!/usr/bin/env python3
import subprocess
import json
import csv
import time
from datetime import datetime
from pathlib import Path
import threading
from collections import deque

# =========================
# CONFIG
# =========================
WINDOW = 60                      
INPUT_ACTIVE_WINDOW = 3.0        
INTERVAL = 1.0                   
# Threshold to consider "real" typing vs just a stray key press
WPM_TYPING_THRESHOLD = 2.0 

PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR / "input_test_log.csv"

# =========================
# GLOBAL STATE
# =========================
keystrokes = deque()
last_keyboard_time = 0.0
last_mouse_time = 0.0
keys_counter = 0

last_window_id = None
window_just_switched = False
last_label = None

# Keys that should NOT trigger a "Typing" label (common for window management)
MODIFIER_KEYS = {"KEY_LEFTMETA", "KEY_RIGHTMETA", "KEY_LEFTALT", "KEY_RIGHTALT", 
                 "KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT",
                 "KEY_TAB", "KEY_ENTER", "KEY_ESC"}

# =========================
# CSV INIT
# =========================
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp", "kb_active", "ms_active", "window_id",
            "avg_wpm", "inst_wpm", "keys_per_sec", "label"
        ])

# =========================
# NIRI WINDOW TRACKER
# =========================
def get_focused_window():
    try:
        result = subprocess.run(
            ["niri", "msg", "-j", "focused-window"],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except Exception:
        return None

# =========================
# INPUT LISTENER
# =========================
def input_listener():
    global last_keyboard_time, last_mouse_time, keys_counter
    
    proc = subprocess.Popen(
        ["libinput", "debug-events"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1
    )

    for line in proc.stdout:
        now = time.time()
        if "KEYBOARD_KEY" in line:
            # Check if this is a "real" typing key or a modifier
            is_modifier = any(mod in line for mod in MODIFIER_KEYS)
            
            if "pressed" in line:
                last_keyboard_time = now
                # Only count non-modifiers towards typing metrics
                if not is_modifier:
                    keystrokes.append(now)
                    keys_counter += 1
                
                while keystrokes and now - keystrokes[0] > WINDOW:
                    keystrokes.popleft()

        elif "POINTER_MOTION" in line or "BUTTON_" in line:
            last_mouse_time = now

# =========================
# NOTIFICATION
# =========================
def send_notification(label, details):
    """Sends a notification that stays longer and doesn't flicker."""
    try:
        # -t 3000 = 3 seconds. 
        # Removed the 'synchronous' hint to ensure it feels more 'stuck' if that's preferred, 
        # but kept a unique tag so it updates the same bubble.
        subprocess.run([
            "notify-send", 
            "-t", "3000", 
            "-h", "string:x-canonical-private-synchronous:input-test-v2",
            f"State: {label}", 
            details
        ])
    except Exception:
        pass

# =========================
# MAIN LOGIC
# =========================
def run_monitor():
    global last_window_id, keys_counter, last_label

    print(f"Monitoring... Logging to {CSV_PATH}")
    threading.Thread(target=input_listener, daemon=True).start()

    while True:
        t0 = time.time()
        
        # 1. Get window data
        win_data = get_focused_window()
        current_win_id = win_data.get("id") if win_data else "none"
        window_switched = (last_window_id is not None and current_win_id != last_window_id)
        last_window_id = current_win_id

        # 2. Get input stats
        kb_active = (time.time() - last_keyboard_time <= INPUT_ACTIVE_WINDOW)
        ms_active = (time.time() - last_mouse_time <= INPUT_ACTIVE_WINDOW)
        
        kps = keys_counter
        keys_counter = 0 # reset window
        inst_wpm = round((kps * 60) / 5, 1)
        avg_wpm = round(len(keystrokes) / 5, 1)

        # 3. Refined Labeling Rule
        # Priority: Typing > Browsing > Idle
        if kps > 0 or inst_wpm > WPM_TYPING_THRESHOLD:
            label = "Typing"
        elif ms_active or window_switched:
            label = "Browsing"
        else:
            label = "Idle"

        # 4. Save and Notify
        row = [
            datetime.now().isoformat(timespec="seconds"),
            int(kb_active), int(ms_active), current_win_id,
            avg_wpm, inst_wpm, kps, label
        ]
        
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

        if label != last_label or (label != "Idle" and int(t0) % 5 == 0):
            detail_str = f"WPM: {inst_wpm} | Win: {current_win_id}\nMouse: {'Active' if ms_active else 'Off'}"
            send_notification(label, detail_str)
            last_label = label

        # Maintain 1s interval
        time.sleep(max(0, INTERVAL - (time.time() - t0)))

if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
