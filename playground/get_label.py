import pandas as pd

INPUT = "unified_activity_log.csv"
OUTPUT = "labeled_activity_log.csv"

df = pd.read_csv(INPUT)

def label_row(r):
    keyboard = r["keyboard_active"]
    mouse = r["mouse_active"]
    keys = r["keys_per_sec"]
    idle = r["idle_time_sec"]
    net_in = r["net_in_Bps"]
    cpu = r["cpu_percent"]
    win_switch = r["window_switch_count"]

    # ---- thresholds ----
    TYPING_KEYS = 1          # ≥1 key/sec = typing
    IDLE_TIME = 5            # ≥5 sec no input = idle
    VIDEO_NET = 500_000      # ~0.5 MB/s sustained inbound
    BUSY_CPU = 40            # background load threshold

    # ---- logic ----
    if keyboard and keys >= TYPING_KEYS:
        return "typing"

    if (mouse or win_switch > 0) and keys < TYPING_KEYS:
        return "browsing"

    if mouse == 0 and net_in >= VIDEO_NET:
        return "watching_video"

    if idle >= IDLE_TIME and cpu >= BUSY_CPU:
        return "background_busy"

    if idle >= IDLE_TIME:
        return "idle"

    return "unknown"

df["label"] = df.apply(label_row, axis=1)
df.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)
