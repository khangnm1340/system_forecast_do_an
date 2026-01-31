import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model

WINDOW_SIZE = 10

model = load_model("cpu_lstm.h5")
scaler = joblib.load("scaler.pkl")

df = pd.read_csv("next5s.csv")

df["timestamp"] = pd.to_datetime(df["timestamp"])
df["timestamp"] = df["timestamp"].astype("int64") / 1e9
df = df.drop(columns=["app_id"])

features = df.drop(columns=["cpu_percent"])
features_scaled = scaler.transform(features)

# take last WINDOW_SIZE seconds
x_input = features_scaled[-WINDOW_SIZE:]
x_input = np.expand_dims(x_input, axis=0)

pred = model.predict(x_input)

print("Predicted CPU usage 5 seconds ahead:", float(pred[0][0]), "%")
