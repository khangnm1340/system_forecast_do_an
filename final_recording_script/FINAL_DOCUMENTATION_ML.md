# System State Forecast: Project Documentation

## 1. Executive Summary

**Goal:** Develop a machine learning system to classify the computer's current state into **Idle**, **Interactive (Light)**, or **Media Watching** in real-time.

**Constraint:** The final deployment must rely **exclusively on system resource metrics** (CPU, RAM, Disk, Network, GPU) and **cannot** use invasive input monitoring (key/mouse logging).

**Outcome:** A Random Forest classifier achieved ~83% accuracy. Critical "Idle" detection was achieved by combining statistical learning with a hardware-aware heuristic override based on GPU sleep states (`RC6`) and maximum engine utilization (`max_gpu`).

---

## 2. System Architecture

The project consists of three main stages: **Data Collection**, **Model Training**, and **Live Inference**.

### 2.1 Data Collection (`10_comprehensive_activity_log.py`)

This script runs as a background daemon to build the training dataset.

*   **Sampling Rate:** 1.0 second.
*   **Data Sources:**
    *   **CPU/RAM/Disk/Net:** via `psutil`.
    *   **GPU Metrics:** via `intel_gpu_top` (CLI tool) parsed in real-time. Captures specific engines:
        *   `RC6`: Render C-State 6 (Sleep/Power Saving).
        *   `RCS`: Render Command Streamer (3D/Compute).
        *   `VCS`: Video Command Streamer (Media Decoding).
        *   `BCS`: Blitter Command Streamer (Memory Copy).
    *   **Ground Truth (Training Only):** Uses `libinput` to calculate `idle_time_sec` (time since last input). This is **removed** from the final model input but used to label the training data.
*   **Output:** `comprehensive_activity_log.csv`.

### 2.2 Feature Engineering

Raw metrics are too volatile for stable prediction. We engineer "Rolling Features" over two time windows:

1.  **Short Window (5s):** Captures immediate state changes (e.g., "Just started typing").
2.  **Long Window (30s):** Captures trends (e.g., "Watching a movie" vs "Loading a webpage").

For every raw metric (e.g., `cpu_percent`), we generate:
*   `cpu_percent_mean_5s`
*   `cpu_percent_std_5s`
*   `cpu_percent_mean_30s`
*   `cpu_percent_std_30s`

**Key Insight:** The `std` (Standard Deviation) features are crucial. "Idle" has low variance, while "Reading" (Light Interactive) has bursts of variance even if the mean is low.

### 2.3 The Model (`system_only_model/train_model.py`)

*   **Algorithm:** Random Forest Classifier.
*   **Why?** Handles non-linear relationships well, robust to noise, and provides feature importance visibility.
*   **Class Weights:**
    *   `Idle`: **5.0** (Heavily prioritized).
    *   `Interactive`: 1.0.
    *   `Media`: 1.0.
    *   *Reasoning:* "Idle" is the minority class and statistically looks very similar to "Light Interactive". We punish the model 5x more for missing an Idle state.
*   **Input Features (Final System-Only Version):**
    *   `cpu_percent`, `ram_percent`
    *   `disk_read_Bps`, `disk_write_Bps`
    *   `net_in_Bps`, `net_out_Bps`
    *   `gpu_RC6_pct` (Sleep %), `gpu_RCS_pct` (3D %), `gpu_VCS_pct` (Video %)
    *   `gpu_Power_W_pkg` (Power draw)
    *   `max_gpu` (The max usage of any single GPU engine)

---

## 3. The "Idle" Detection Challenge

The core technical hurdle was distinguishing **Idle** from **Light Interactive** (e.g., reading a static web page) without checking mouse/keyboard inputs.

### The Problem
*   **Idle:** CPU ~1-2%, GPU Sleep ~99%.
*   **Reading:** CPU ~2-3%, GPU Sleep ~97%.
*   To a standard model, these distributions overlap by >80%. The model initially failed to predict "Idle" entirely, defaulting to "Interactive".

### The Solution: `max_gpu` & Heuristics

1.  **Feature Discovery:** We analyzed the data and found that `max_gpu` (the highest load on *any* GPU sub-engine) was the most discriminative feature.
    *   When **truly idle**, `max_gpu` is often **0.0** or **<1.0**.
    *   When **reading**, background rendering (browser compositing) causes micro-spikes in `max_gpu` even if the average is low.
2.  **Model Retraining:** We added `max_gpu` to the training set, making it the #2 most important feature.
3.  **Heuristic Override (The "Silver Bullet"):**
    Since ML is probabilistic, we added a **hard logic rule** in the inference engine to guarantee Idle detection when the hardware is effectively silent.

    ```python
    # Logic in live_inference.py
    if prediction == 'interactive_light':
        # Condition 1: Deep GPU Sleep (>99%) AND Low CPU (<5%)
        quiet_system = (rc6_mean_5s > 99.0 and cpu_mean_5s < 5.0)
        
        # Condition 2: GPU is effectively off
        gpu_dead = (max_gpu_raw < 1.0)

        if quiet_system or gpu_dead:
            prediction = 'Idle'  # Force Override
    ```

---

## 4. File Structure & Manifest

| File | Description |
| :--- | :--- |
| `10_comprehensive_activity_log.py` | **Data Collector.** Runs in background. Connects to OS metrics and writes to CSV. |
| `system_only_model/` | **Production Directory.** Contains the final "Input-Free" version of the project. |
| ├── `train_model.py` | **Trainer.** Loads CSV, generates rolling features, trains Random Forest, saves `.joblib`. |
| ├── `live_inference.py` | **The Brain.** Tails the CSV log, computes features in real-time, applies overrides, and predicts. |
| ├── `activity_model.joblib` | **The Model.** serialized Random Forest model. |
| ├── `analyze_gpu_diff.py` | **Debug Tool.** Used to verify the statistical difference between Idle and Interactive. |
| `state_switching_script.sh` | **Utility.** Helper to switch labels in `current_state.txt` for training data tagging. |

---

## 5. Usage Instructions

### Step 1: Start Data Collection
This must run in the background to feed data to the system.
```bash
sudo uv run 10_comprehensive_activity_log.py
```
*(Note: `sudo` is often required for `intel_gpu_top` access).*

### Step 2: Inference (Production)
Run the system-only inference engine. It triggers system notifications (`notify-send`) on state change.
```bash
uv run system_only_model/live_inference.py
```

### Step 3: Retraining (Maintenance)
If you gather more data or want to tweak behavior:
1.  Ensure `comprehensive_activity_log_with_Idle.csv` is updated.
2.  Run:
    ```bash
    cd system_only_model
    uv run train_model.py
    ```

---

## 6. Technical Specifications

*   **Python Version:** 3.10+
*   **Key Libraries:** `pandas`, `scikit-learn`, `psutil`, `joblib`.
*   **External Dependencies:** `intel-gpu-tools` (for `intel_gpu_top`), `libinput-tools` (only for initial labeled data collection).

## 7. Future Improvements
*   **Hysteresis:** Add a "state latch" to prevent flickering. e.g., "Must predict IDLE for 3 consecutive seconds to switch."
*   **Per-Process Analysis:** If specific apps (e.g., `mpv`, `vlc`) are focused, hard-code "Media" state regardless of resource usage.
