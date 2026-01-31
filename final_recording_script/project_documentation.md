# System State Forecast: Predicting User State via Resource Metrics

## 1. Project Overview
This project documents the development of a machine learning system designed to classify a user's current state—**Idle**, **Interactive (Light)**, or **Media Watching**—using only non-invasive system resource metrics (CPU, RAM, Disk, Network, and GPU).

The project evolved from an initial attempt to predict raw resource usage into a classification system that understands user behavior through the "fingerprint" left on the hardware.

---

## 2. Phase 1: The Initial Concept & Pivot
### 2.1 The Goal: Predicting CPU Usage
Initially, the objective was to forecast future CPU/RAM usage based on past behavior, including command history, window titles, and time of day. 

### 2.2 The Problem
After collecting significant data (approximately 58,000 rows across three users), we discovered two critical flaws:
1.  **Skewed Distribution:** For 99.9% of the time, system usage stayed between 5-15%. A model could achieve "high accuracy" simply by guessing 10%, which provided no utility.
2.  **Unpredictable Peaks:** Resource spikes (e.g., compiling code or launching a game) are driven by user intent, which is not visible in historical system usage alone. 

**Conclusion:** We cannot predict *when* a user will start a heavy task, but we can predict *what* the user is currently doing based on how the system reacts.

---

## 3. Phase 2: The Realized Topic (User State Classification)
We pivoted to classifying the user's state into three categories:
*   **Idle:** System is quiet, no user interaction.
*   **Interactive (Light):** Coding, browsing, reading, or texting.
*   **Media Playback:** Watching videos or movies.

*Note: "Interactive Heavy" (gaming/training models/compling code) and "Background Downloads" were excluded as they are easily identifiable via simple threshold rules (e.g., Net In > X Mbps) and do not require complex ML.*

---

## 4. Data Collection Architecture
The group (4 members) used **Arch Linux** with the **Niri** window manager. This environment allowed for deep, scriptable access to system states.

### 4.1 Data Sources
*   **System Metrics:** Captured via `psutil` (CPU, RAM, Disk I/O, Network I/O).
*   **Window Context:** Captured via `niri msg -j focused-window` (app_id and window titles).
*   **Input Metrics:** Captured via `libinput debug-events`. We calculated WPM (Words Per Minute), keys per second, and "typing bursts" to provide ground truth for the model.
*   **GPU Metrics:** We discovered that GPU sub-engines are the "smoking gun" for state detection. We used `intel_gpu_top`.
We were having a lot of trouble recording the gpu, so we even cloned `btop` a system resource live monitoring tool and (tell AI) to scan the source code to see how they're doing it. (Btop used cpp used a bundled/adapted version of `intel_gpu_top`)

> **Technical Note:** To run `intel_gpu_top` without constant sudo prompts, we applied the following capability:
> ```bash
> sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top
> ```

### 4.2 Verification Tool
To ensure our logging was accurate, we developed a validation script in `nu` that sent real-time notifications of the captured data.

```nu
# Validation script to verify data collection integrity
def main [...params: string] {
  loop {
    open comprehensive_activity_log.csv | last | select ...$params | notify-send -t 1000 $"($in)"
    sleep 1sec
  }
}
```

![Screenshot Placeholder: Notification bubble showing real-time CSV metrics]

---

## 5. Labeling Strategy: Manual-but-Correct
Instead of relying on fuzzy logic to label our training data, we used a hardware-triggered approach.

1.  **Manual Tagging:** We bound keyboard shortcuts in Niri to specific states. When a user started watching a movie, they hit a shortcut that updated `current_state.txt`.
2.  **Heuristic "Idle" Tagging:** For the "Idle" state, we post-processed the data. If `idle_time_sec` (from libinput) was > 10 seconds and the state wasn't "Media Watching," it was automatically re-labeled as "Idle."
3.  **The Dataset:**
    *   User A: 32,000 lines.
    *   User B: 6,000 lines.
    *   User C (Windows - converted): 20,000 lines.

---

## 6. Feature Engineering
Raw metrics are too noisy for stable classification. We implemented **Rolling Features** over two windows:
*   **Short Window (5s):** Captures sudden bursts (e.g., a page load).
*   **Long Window (30s):** Captures sustained patterns (e.g., a 24fps video stream).

**The "Max GPU" Insight:** We found that `max_gpu` (the highest load on any single engine like RCS or VCS) was the most discriminative feature for distinguishing between "Idle" and "Reading."

---

## 7. The Model & Inference Engine
We utilized a **Random Forest Classifier** because it handles the non-linear relationship between resource spikes and user states effectively.

### 7.1 The "Idle" Challenge
The model initially struggled to distinguish between "Idle" and "Light Reading" because the CPU/RAM usage is nearly identical. 

### 7.2 The Solution: Hybrid Heuristics
We combined ML with a hardware-aware override in the inference engine:
```python
# Logic used in live_inference.py
if prediction == 'interactive_light':
    # If the GPU is in deep sleep (RC6) and CPU is low, it's actually Idle
    if (rc6_mean_5s > 99.0 and cpu_mean_5s < 5.0) or (max_gpu_raw < 1.0):
        prediction = 'Idle'
```

![Screenshot Placeholder: Confusion Matrix showing 83% accuracy and high precision for Idle states]
at first the model accuracy went up to 90% and 100% for idling, but I realized it was reading from `idle_time_sec`

---

## 8. Final Outcomes
*   **Accuracy:** ~83% across test sets.
*   **Privacy:** The system classifies state without ever logging specific keystrokes or sensitive window titles in the production inference phase.
*   **Responsiveness:** Real-time state detection with a 1-second sampling rate.

### Future Work
*   Implementing **Hysteresis** to prevent "flickering" between states.
*   Expanding the model to support "Profiles" (e.g., Gamer vs. Programmer) to account for different baseline resource usages.
