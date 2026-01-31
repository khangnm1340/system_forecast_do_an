import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import sys

# 1. Load Data
FILE_PATH = 'comprehensive_activity_log_with_Idle.csv'
print(f"Loading data from {FILE_PATH}...")
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"Error: {FILE_PATH} not found.")
    sys.exit(1)

# Sort by time
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# 2. Feature Selection
numeric_cols = [
    'cpu_percent', 'ram_percent', 
    'disk_read_Bps', 'disk_write_Bps',
    'net_in_Bps', 'net_out_Bps',
    'idle_time_sec',
    'gpu_RC6_pct', 'gpu_RCS_pct', 'gpu_VCS_pct',
    'gpu_Power_W_pkg'
]

target_col = 'label'

# 3. Feature Engineering
print("Engineering rolling features...")
df_features = df[numeric_cols].copy()

windows = [5, 30]

for col in numeric_cols:
    for w in windows:
        df_features[f'{col}_mean_{w}s'] = df_features[col].rolling(window=w, min_periods=1).mean()
        df_features[f'{col}_std_{w}s'] = df_features[col].rolling(window=w, min_periods=1).std().fillna(0)

# Drop initial rows for training stability
df_features = df_features.iloc[max(windows):]
y = df.iloc[max(windows):][target_col]
df_features = df_features.fillna(0)

# 4. Train/Test Split
split_idx = int(len(df_features) * 0.8)
X_train = df_features.iloc[:split_idx]
y_train = y.iloc[:split_idx]
X_test = df_features.iloc[split_idx:]
y_test = y.iloc[split_idx:]

# 5. Model Training
print("Training Random Forest Classifier...")
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

# 6. Evaluation
print("Evaluating model...")
y_pred = rf.predict(X_test)
print(classification_report(y_test, y_pred))

# 7. Save Model
print("Saving model to activity_model.joblib...")
joblib.dump(rf, 'activity_model.joblib')
print("Done.")
