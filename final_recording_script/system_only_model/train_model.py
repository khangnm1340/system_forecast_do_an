import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# 1. Load Data
FILE_PATH = 'comprehensive_activity_log_with_Idle.csv'
print(f"Loading data from {FILE_PATH}...")
df = pd.read_csv(FILE_PATH)

# Sort by time just in case, though logs should be ordered
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# 2. Feature Selection
# Define raw columns we care about
numeric_cols = [
    'cpu_percent', 'ram_percent', 
    'disk_read_Bps', 'disk_write_Bps',
    'net_in_Bps', 'net_out_Bps',
    'gpu_RC6_pct', 'gpu_RCS_pct', 'gpu_VCS_pct',
    'gpu_Power_W_pkg',
    'max_gpu'
]

target_col = 'label'

# 3. Feature Engineering
print("Engineering rolling features...")
df_features = df[numeric_cols].copy()

# Add rolling window statistics
# We use a 10-second window to capture immediate context
# and a 60-second window to capture longer term trends
windows = [5, 30]

for col in numeric_cols:
    for w in windows:
        # Mean: smooths signal
        df_features[f'{col}_mean_{w}s'] = df_features[col].rolling(window=w, min_periods=1).mean()
        # Std: captures volatility (e.g. constant video stream vs bursty web loading)
        df_features[f'{col}_std_{w}s'] = df_features[col].rolling(window=w, min_periods=1).std().fillna(0)

# Drop initial rows where rolling features might be unstable (optional, handled by min_periods=1 effectively)
# But for cleaner training, let's drop the first max_window rows
# Assuming max(windows) is defined elsewhere or should be calculated
# For now, let's assume it's 30 based on the windows list
max_window = max(windows) if windows else 0
df_features = df_features.iloc[max_window:]
y = df.iloc[max_window:][target_col]

# Handle any remaining NaNs
df_features = df_features.fillna(0)

# 4. Train/Test Split (Time-series aware)
# We do NOT shuffle. We split by time index.
split_idx = int(len(df_features) * 0.8)

X_train = df_features.iloc[:split_idx]
y_train = y.iloc[:split_idx]

X_test = df_features.iloc[split_idx:]
y_test = y.iloc[split_idx:]

print(f"Training samples: {len(X_train)}")
print(f"Testing samples:  {len(X_test)}")

# 5. Model Training
print("Training Random Forest Classifier...")
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    class_weight={'Idle': 5, 'interactive_light': 1, 'media_watching': 1}, # Force model to prioritize finding Idle
    random_state=42,
    n_jobs=-1
)

rf.fit(X_train, y_train)

# 6. Evaluation
print("Evaluating model...")
y_pred = rf.predict(X_test)

print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred))

print("\n--- Confusion Matrix ---")
cm = confusion_matrix(y_test, y_pred)
print(cm)

# 7. Feature Importance
importances = rf.feature_importances_
feature_names = X_train.columns
feature_imp_df = pd.DataFrame({'feature': feature_names, 'importance': importances})
feature_imp_df = feature_imp_df.sort_values('importance', ascending=False).head(15)

print("\n--- Top 15 Important Features ---")
print(feature_imp_df)

# Optional: Plotting (if running in a notebook or saving to file)
# plt.figure(figsize=(10,6))
# sns.barplot(x='importance', y='feature', data=feature_imp_df)
# plt.title('Feature Importance')
# plt.tight_layout()
# plt.savefig('feature_importance.png')

# 8. Save Model
print("Saving model to activity_model.joblib...")
joblib.dump(rf, 'activity_model.joblib')
print("Done.")
