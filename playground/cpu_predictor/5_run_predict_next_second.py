#!/usr/bin/env python3

import time
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# ======================
# CONFIG
# ======================

CSV_PATH   = Path("system_metrics.csv")
MODEL_PATH = Path("cpu_predictor.pkl")
SCALER_PATH = Path("scaler.pkl")

WINDOW = 30
POLL_INTERVAL = 1.0   # seconds

FEATURE_COLS = [
    "cpu_percent",
    "ram_percent",
    "disk_read_Bps",
    "disk_write_Bps",
    "net_in_Bps",
    "net_out_Bps"
]

# ======================
# LOAD MODEL + SCALER
# ======================

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

print("Real-time CPU predictor started...")

# ======================
# MAIN LOOP
# ======================

while True:
    try:
        # Read last WINDOW lines efficiently
        df = pd.read_csv(CSV_PATH)

        if len(df) < WINDOW:
            print("Waiting for more data...")
            time.sleep(POLL_INTERVAL)
            continue

        last_rows = df[FEATURE_COLS].tail(WINDOW)

        # Scale using training scaler
        scaled = scaler.transform(last_rows.values)

        # Flatten into model input shape
        X = scaled.flatten().reshape(1, -1)

        # Predict scaled cpu
        pred_scaled = model.predict(X)[0]

        # Convert prediction back to real CPU %
        # Inverse transform trick: only cpu column matters
        dummy = np.zeros((1, len(FEATURE_COLS)))
        dummy[0, 0] = pred_scaled
        cpu_pred = scaler.inverse_transform(dummy)[0, 0]

        print(f"Predicted next-second CPU: {cpu_pred:.2f}%")

    except Exception as e:
        print("Error:", e)

    time.sleep(POLL_INTERVAL)
