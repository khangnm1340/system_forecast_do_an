import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import time

# ----------------------------
# Config
# ----------------------------

CSV_PATH = "system_metrics.csv"   # live-updating file
MODEL_PATH = "cpu_predictor.pt"
SCALER_PATH = "scaler.save"

SEQ_LEN = 120
POLL_INTERVAL = 1  # seconds

# ----------------------------
# Model definition
# ----------------------------

class LSTMModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, 64, batch_first=True)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.fc(out)
        return out

# ----------------------------
# Load scaler and model
# ----------------------------

scaler = joblib.load(SCALER_PATH)

# Determine input feature count from CSV
tmp = pd.read_csv(CSV_PATH, nrows=1)
tmp["timestamp"] = pd.to_datetime(tmp["timestamp"])
tmp["time_sec"] = tmp["timestamp"].astype("int64") // 10**9
tmp = tmp.drop(columns=["timestamp"])   # KEEP cpu_percent
input_size = tmp.shape[1]

model = LSTMModel(input_size)
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()

print("Model loaded. Waiting for data...")

# ----------------------------
# Load latest sequence
# ----------------------------

def load_latest_sequence():
    df = pd.read_csv(CSV_PATH)

    if len(df) < SEQ_LEN:
        return None

    # Timestamp → numeric
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["time_sec"] = df["timestamp"].astype("int64") // 10**9
    df = df.drop(columns=["timestamp"])

    # All remaining columns INCLUDING cpu_percent are features
    features = df.values.astype(np.float32)

    # Normalize with training scaler
    features = scaler.transform(features)

    # Take last SEQ_LEN timesteps
    seq = features[-SEQ_LEN:]
    seq = torch.tensor(seq).unsqueeze(0)  # shape: (1, seq_len, features)

    return seq

# ----------------------------
# Prediction loop
# ----------------------------

while True:
    seq = load_latest_sequence()

    if seq is not None:
        with torch.no_grad():
            pred = model(seq)
            cpu_next = pred.item()
            print(f"Predicted next CPU usage: {cpu_next:.2f}%")

    time.sleep(POLL_INTERVAL)
