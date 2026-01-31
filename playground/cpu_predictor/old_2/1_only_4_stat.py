import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset, DataLoader
import torch
import torch.nn as nn
import joblib

CSV_PATH = "system_metrics.csv"
SEQ_LEN = 20
BATCH_SIZE = 64
EPOCHS = 20
LR = 1e-3

# ----------------------------
# Load data
# ----------------------------

df = pd.read_csv(CSV_PATH)

df["timestamp"] = pd.to_datetime(df["timestamp"])
df["time_sec"] = df["timestamp"].astype("int64") // 10**9
df = df.drop(columns=["timestamp"])

# All columns INCLUDING cpu_percent are input features
features = df.values.astype(np.float32)

# Target is next-timestep cpu_percent (column index 0)
cpu_index = df.columns.get_loc("cpu_percent")
target = features[:, cpu_index]

# Normalize all features
scaler = StandardScaler()
features = scaler.fit_transform(features)

joblib.dump(scaler, "scaler.save")

# ----------------------------
# Build sequences
# ----------------------------

X_seq = []
y_seq = []

for i in range(len(features) - SEQ_LEN):
    X_seq.append(features[i:i+SEQ_LEN])
    y_seq.append(target[i+SEQ_LEN])  # next cpu_percent

X_seq = np.array(X_seq)
y_seq = np.array(y_seq).reshape(-1,1)

# Train/test split
split = int(0.8 * len(X_seq))
X_train, X_test = X_seq[:split], X_seq[split:]
y_train, y_test = y_seq[:split], y_seq[split:]

# ----------------------------
# Dataset
# ----------------------------

class CPUDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X)
        self.y = torch.tensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        return self.X[i], self.y[i]

train_loader = DataLoader(CPUDataset(X_train, y_train), batch_size=BATCH_SIZE, shuffle=True)

# ----------------------------
# Model
# ----------------------------

class LSTMModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, 64, batch_first=True)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        out,_ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)

model = LSTMModel(input_size=X_train.shape[2])

optimizer = torch.optim.Adam(model.parameters(), lr=LR)
loss_fn = nn.MSELoss()

# ----------------------------
# Train
# ----------------------------

for epoch in range(EPOCHS):
    total = 0
    for Xb, yb in train_loader:
        pred = model(Xb)
        loss = loss_fn(pred, yb)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total += loss.item()
    print(f"Epoch {epoch+1}: loss={total/len(train_loader):.4f}")

# ----------------------------
# Save model
# ----------------------------

torch.save(model.state_dict(), "cpu_predictor.pt")

print("Training complete. New model saved.")
