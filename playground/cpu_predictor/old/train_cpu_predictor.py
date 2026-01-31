import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import joblib

# ======================
# Config
# ======================

CSV_PATH = "unified_activity_log.csv"     # your dataset file
WINDOW_SIZE = 10             # use last 10 seconds of data
PREDICT_AHEAD = 5            # predict cpu 5 seconds in future
MODEL_OUT = "cpu_lstm.h5"
SCALER_OUT = "scaler.pkl"

# ======================
# Load Data
# ======================

df = pd.read_csv(CSV_PATH)

# Convert timestamp to numeric seconds (optional but useful)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["timestamp"] = df["timestamp"].astype("int64") / 1e9

# Drop non-numeric categorical IDs or encode simply
df = df.drop(columns=["app_id"])   # string column
# window_id and pid are numeric but arbitrary IDs — still ok to keep

# ======================
# Prepare Features
# ======================

features = df.drop(columns=["cpu_percent"])
target = df["cpu_percent"].values

scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

joblib.dump(scaler, SCALER_OUT)

# ======================
# Build sliding windows
# ======================

X = []
y = []

for i in range(len(features_scaled) - WINDOW_SIZE - PREDICT_AHEAD):
    X.append(features_scaled[i:i+WINDOW_SIZE])
    y.append(target[i+WINDOW_SIZE+PREDICT_AHEAD-1])

X = np.array(X)
y = np.array(y)

print("X shape:", X.shape)
print("y shape:", y.shape)

# ======================
# Model
# ======================

model = Sequential([
    LSTM(64, input_shape=(WINDOW_SIZE, X.shape[2]), return_sequences=True),
    Dropout(0.2),
    LSTM(32),
    Dense(16, activation="relu"),
    Dense(1)
])

model.compile(optimizer="adam", loss="mse")

model.summary()

# ======================
# Train
# ======================

es = EarlyStopping(patience=5, restore_best_weights=True)

model.fit(
    X, y,
    epochs=50,
    batch_size=32,
    validation_split=0.2,
    callbacks=[es]
)

model.save(MODEL_OUT)

print("Model saved to", MODEL_OUT)
