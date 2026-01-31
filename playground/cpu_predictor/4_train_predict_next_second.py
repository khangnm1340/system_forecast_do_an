#!/usr/bin/env python3

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

# ======================
# CONFIG
# ======================
CSV_PATH = "cpu_ram_disk_net.csv"       # your file
WINDOW = 30                 # seconds of history used
MODEL_OUT = "cpu_predictor.pkl"
SCALER_OUT = "scaler.pkl"

# ======================
# LOAD DATA
# ======================

df = pd.read_csv(CSV_PATH)

# Ensure correct column order
FEATURE_COLS = [
    "cpu_percent",
    "ram_percent",
    "disk_read_Bps",
    "disk_write_Bps",
    "net_in_Bps",
    "net_out_Bps"
]

df = df[FEATURE_COLS]

# ======================
# NORMALIZATION
# ======================

scaler = StandardScaler()
scaled_data = scaler.fit_transform(df.values)

# Save scaler for later inference
joblib.dump(scaler, SCALER_OUT)

# ======================
# BUILD SLIDING WINDOWS
# ======================
# X shape: (samples, WINDOW * features)
# y: next-second cpu_percent

X = []
y = []

for i in range(len(scaled_data) - WINDOW):
    window_slice = scaled_data[i:i+WINDOW].flatten()
    target_cpu = scaled_data[i+WINDOW][0]  # cpu_percent column index = 0
    
    X.append(window_slice)
    y.append(target_cpu)

X = np.array(X)
y = np.array(y)

print("Dataset shape:", X.shape, y.shape)

# ======================
# TRAIN / TEST SPLIT
# ======================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

# ======================
# TRAIN MODEL
# ======================

model = LinearRegression()
model.fit(X_train, y_train)

# ======================
# EVALUATE
# ======================

pred = model.predict(X_test)
mse = mean_squared_error(y_test, pred)

print("Test MSE:", mse)

# ======================
# SAVE MODEL
# ======================

joblib.dump(model, MODEL_OUT)

print("Saved model to:", MODEL_OUT)
print("Saved scaler to:", SCALER_OUT)
