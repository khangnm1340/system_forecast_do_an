import time
import pandas as pd
import joblib
import sys
import os
import subprocess
from collections import deque

# Configuration
MODEL_PATH = 'activity_model.joblib'
CSV_PATH = 'comprehensive_activity_log.csv' # Default, can be changed
MAX_WINDOW = 30 # We need at least 30s of history for features
POLL_INTERVAL = 0.5 # Seconds to sleep between checks

# Features used in training (MUST MATCH EXACTLY)
NUMERIC_COLS = [
    'cpu_percent', 'ram_percent', 
    'disk_read_Bps', 'disk_write_Bps',
    'net_in_Bps', 'net_out_Bps',
    'idle_time_sec',
    'gpu_RC6_pct', 'gpu_RCS_pct', 'gpu_VCS_pct',
    'gpu_Power_W_pkg'
]
WINDOWS = [5, 30]

def load_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model file {MODEL_PATH} not found. Run train_model.py first.")
        sys.exit(1)
    return joblib.load(MODEL_PATH)

def calculate_features(buffer_df):
    """
    Takes a DataFrame of the last N seconds and calculates the single 
    feature row for the *latest* timestamp.
    """
    # Create a single row dataframe for the result
    current_row = buffer_df.iloc[[-1]].copy()
    
    # We need to compute features based on the history in buffer_df
    # For the last row, the rolling window looks back at buffer_df
    
    features = {}
    
    for col in NUMERIC_COLS:
        series = buffer_df[col]
        for w in WINDOWS:
            # We only care about the value for the *last* row
            # rolling().mean() returns a series, we take the last value
            if len(series) >= 1:
                # We limit the rolling calculation to the tail to be efficient, 
                # but pandas rolling is optimized anyway.
                # However, strictly, rolling(w) needs w elements.
                # min_periods=1 ensures we get a result even if buffer is small (startup)
                
                # Slice the series to the relevant window size + a bit for safety, though pandas handles it
                # Actually, simplest is to just compute rolling on the whole buffer and take the last one
                rolled_mean = series.rolling(window=w, min_periods=1).mean().iloc[-1]
                rolled_std = series.rolling(window=w, min_periods=1).std().fillna(0).iloc[-1]
                
                features[f'{col}_mean_{w}s'] = rolled_mean
                features[f'{col}_std_{w}s'] = rolled_std
            else:
                features[f'{col}_mean_{w}s'] = 0.0
                features[f'{col}_std_{w}s'] = 0.0
    
    # Add raw columns to features (model expects them)
    if len(buffer_df) > 0:
        last_row = buffer_df.iloc[-1]
        for col in NUMERIC_COLS:
            features[col] = last_row[col]
    else:
        for col in NUMERIC_COLS:
            features[col] = 0.0
                
    return pd.DataFrame([features])

def main():
    target_file = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    print(f"Loading model from {MODEL_PATH}...")
    model = load_model()
    
    print(f"Monitoring {target_file} for real-time inference...")
    
    last_prediction = None
    
    # Initialize buffer
    # We use a fixed-size buffer logic
    # First, read existing file to populate buffer
    try:
        # Read only the columns we need to save memory/time, plus maybe timestamp if needed for debugging
        # But pandas read_csv is fast enough for typical log files.
        # simpler: read the last 60 lines
        df_init = pd.read_csv(target_file)
        # Keep only necessary columns
        df_buffer = df_init[NUMERIC_COLS].tail(MAX_WINDOW * 2).copy() # Keep a bit more for safety
        print(f"Initialized buffer with {len(df_buffer)} rows.")
    except FileNotFoundError:
        print("File not found, waiting for it to be created...")
        df_buffer = pd.DataFrame(columns=NUMERIC_COLS)

    # Open file for tailing
    with open(target_file, 'r') as f:
        # Move to end of file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                continue
            
            # Parse line
            try:
                # Assuming CSV structure is known and constant.
                # We can't use pd.read_csv on a single line string easily without header
                # So we parse manually or use io.StringIO
                from io import StringIO
                # We need the header to map columns correctly. 
                # We assume the file *has* a header and we know the column order from df_init
                # If the file is just being appended to, the new line doesn't have a header.
                # We rely on the column order being consistent with NUMERIC_COLS?
                # No, the CSV has many columns. We need to map them by index or name.
                
                # Robust way: Read the header once, store column names -> indices map
                # But we already read the whole file into df_init.
                # Let's just use the column names from df_init.columns
                
                # Parse the single line using pandas by creating a mini-csv string with header
                # This is slightly inefficient but robust against column reordering if we had the header.
                # Since we only have the data line, we MUST assume column order matches the file header.
                
                # Let's look at the header from the file again
                # timestamp,cpu_percent,ram_percent,disk_read_Bps,...
                
                # Fast and dirty: split by comma
                parts = line.strip().split(',')
                if len(parts) < len(NUMERIC_COLS): 
                    # incomplete line or empty
                    continue
                
                # We need to map values to NUMERIC_COLS.
                # We can learn the mapping from the header we read earlier.
                if 'header_map' not in locals():
                    # Read header line
                    with open(target_file, 'r') as f_head:
                        header_line = f_head.readline().strip()
                        headers = header_line.split(',')
                        header_map = {name: i for i, name in enumerate(headers)}
                
                # Extract only the numeric columns we need
                row_data = {}
                for col in NUMERIC_COLS:
                    idx = header_map.get(col)
                    if idx is not None and idx < len(parts):
                        try:
                            row_data[col] = float(parts[idx])
                        except ValueError:
                            row_data[col] = 0.0
                    else:
                        row_data[col] = 0.0 # Default if missing
                
                # Append to buffer
                new_row_df = pd.DataFrame([row_data])
                df_buffer = pd.concat([df_buffer, new_row_df], ignore_index=True)
                
                # Trim buffer
                if len(df_buffer) > MAX_WINDOW * 2:
                    df_buffer = df_buffer.iloc[-(MAX_WINDOW * 2):]
                
                # Calculate Features
                # We only need to predict for the LATEST row
                X_input = calculate_features(df_buffer)
                
                # Predict
                # Ensure column order matches training
                # The dataframe created by calculate_features usually sorts columns or uses dict order.
                # The model expects specific column order.
                # We should reorder X_input to match model.feature_names_in_ if available
                if hasattr(model, 'feature_names_in_'):
                    X_input = X_input[model.feature_names_in_]
                
                prediction = model.predict(X_input)[0]
                probs = model.predict_proba(X_input)[0]
                max_prob = max(probs)
                
                # Print result
                timestamp = parts[0] # Assuming timestamp is first col
                print(f"[{timestamp}] State: {prediction:<20} (Conf: {max_prob:.2f})")

                # Notify on change
                if prediction != last_prediction:
                    subprocess.run(["notify-send", "-t", "2000", "System State Change", f"Detected: {prediction}\nConfidence: {max_prob:.2f}"])
                    last_prediction = prediction
                
            except Exception as e:
                # Don't crash on a bad line
                print(f"Error processing line: {e}")
                continue

if __name__ == "__main__":
    main()
