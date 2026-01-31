#!/usr/bin/env python3
import time
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression

CSV_PATH = Path("combined_log.csv")

# =========================
# CONFIG
# =========================
WINDOW_SIZE = 10
PREDICT_AHEAD = 5
TARGET_COL = "cpu_percent"
INTERVAL = 1.0

USE_COLS = [
    "cpu_percent",
    "ram_percent",
    "disk_read_Bps",
    "net_out_Bps",
]

model = LinearRegression()
scaler = MinMaxScaler()
last_trained_rows = 0


def load_data():
    df = pd.read_csv(CSV_PATH)

    # chỉ giữ 4 cột cần thiết
    df = df[USE_COLS]

    return df


def build_dataset(scaled):
    X, y = [], []
    target_idx = USE_COLS.index(TARGET_COL)

    for i in range(len(scaled) - WINDOW_SIZE - PREDICT_AHEAD):
        X.append(scaled[i:i + WINDOW_SIZE].flatten())
        y.append(scaled[i + WINDOW_SIZE + PREDICT_AHEAD][target_idx])

    return np.array(X), np.array(y)


while True:
    try:
        df = load_data()

        if len(df) < WINDOW_SIZE + PREDICT_AHEAD + 5:
            time.sleep(1)
            continue

        # =========================
        # NORMALIZE
        # =========================
        scaled = scaler.fit_transform(df)

        # =========================
        # TRAIN (khi có data mới)
        # =========================
        if len(df) != last_trained_rows:
            X, y = build_dataset(scaled)

            if len(X) > 10:
                model.fit(X, y)
                last_trained_rows = len(df)

        # =========================
        # PREDICT t + 5s
        # =========================
        last_window = scaled[-WINDOW_SIZE:].flatten().reshape(1, -1)
        pred_norm = model.predict(last_window)[0]

        cpu_idx = USE_COLS.index(TARGET_COL)
        cpu_min = scaler.data_min_[cpu_idx]
        cpu_max = scaler.data_max_[cpu_idx]

        cpu_pred = pred_norm * (cpu_max - cpu_min) + cpu_min

        print(
            f"⏱ now | 🔮 CPU @ t+{PREDICT_AHEAD}s ≈ {cpu_pred:.2f}%"
        )

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(INTERVAL)
