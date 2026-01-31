# System State Forecast: Predicting User State via Resource Metrics

## 1. Project Overview
This project documents the development of a machine learning system designed to classify a user's current state—**Idle**, **Interactive (Light)**, or **Media Watching**—using only non-invasive system resource metrics (CPU, RAM, Disk, Network, and GPU).

The project evolved from an initial attempt to predict raw resource usage into a classification system that understands user behavior through the "fingerprint" left on the hardware.

---

## 2. Phase 1: The Initial Concept & Pivot
### 2.1 The Goal: Predicting CPU Usage
Initially, the objective was to forecast future CPU/RAM usage based on past behavior, including command history, window titles, and time of day. 

### 2.2 The Problem
After collecting significant data (approximately 70 rows across three users), we discovered two critical flaws:
1.  **Skewed Distribution:** For 99.9% of the time, system usage stayed between 5-15%. A model could achieve "high accuracy" simply by guessing 10%, which provided no utility.
2.  **Unpredictable Peaks:** Resource spikes (e.g., compiling code or launching a game) are driven by user intent, which is not visible in historical system usage alone. 

**Conclusion:** We cannot predict *when* a user will start a heavy task, but we can predict *what* the user is currently doing based on how the system reacts.

3.  **The Dataset collected:**
    *   User A: 42,000 lines.
    *   User B: 6,000 lines.
    *   User C (Windows - converted): 20,000 lines.


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
    *  11,000 lines.
added waybar module

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

# this is the first model , accuracy is really high, but I realized it was reading from `idle_time_sec`, So I retrained it (see the next model)
↪ uv run train_model.py
Loading data from comprehensive_activity_log_with_Idle.csv...
Engineering rolling features...
Training samples: 8696
Testing samples:  2175
Training Random Forest Classifier...
Evaluating model...

--- Classification Report ---
                   precision    recall  f1-score   support

             Idle       0.70      1.00      0.82       175
interactive_light       0.83      0.97      0.89       879
   media_watching       0.97      0.77      0.86      1121

         accuracy                           0.87      2175
        macro avg       0.83      0.92      0.86      2175
     weighted avg       0.89      0.87      0.87      2175


--- Confusion Matrix ---
[[175   0   0]
 [  0 855  24]
 [ 75 178 868]]

--- Top 15 Important Features ---
                     feature  importance
47       gpu_VCS_pct_mean_5s    0.104796
35     idle_time_sec_mean_5s    0.080839
6              idle_time_sec    0.078176
48        gpu_VCS_pct_std_5s    0.066708
11       cpu_percent_mean_5s    0.059929
13      cpu_percent_mean_30s    0.056203
9                gpu_VCS_pct    0.052756
41      gpu_RC6_pct_mean_30s    0.048737
7                gpu_RC6_pct    0.047768
39       gpu_RC6_pct_mean_5s    0.046157
45      gpu_RCS_pct_mean_30s    0.037689
53  gpu_Power_W_pkg_mean_30s    0.034496
42       gpu_RC6_pct_std_30s    0.032940
43       gpu_RCS_pct_mean_5s    0.031594
49      gpu_VCS_pct_mean_30s    0.028173
Saving model to activity_model.joblib...
Done.

# the second retrained model(not with `idle_time_sec` feature), even though accuracy is lower, for live inferecing, it was really good, for some reason
↪ uv run train_model.py
Loading data from comprehensive_activity_log_with_Idle.csv...
Engineering rolling features...
Training samples: 8696
Testing samples:  2175
Training Random Forest Classifier...
Evaluating model...

--- Classification Report ---
                   precision    recall  f1-score   support

             Idle       0.53      0.59      0.56       175
interactive_light       0.76      0.94      0.84       879
   media_watching       0.97      0.76      0.85      1121

         accuracy                           0.82      2175
        macro avg       0.75      0.77      0.75      2175
     weighted avg       0.85      0.82      0.82      2175


--- Confusion Matrix ---
[[104  71   0]
 [ 22 827  30]
 [ 71 195 855]]

--- Top 15 Important Features ---
                     feature  importance
35       gpu_RC6_pct_mean_5s    0.104772
51           max_gpu_mean_5s    0.085098
13      cpu_percent_mean_30s    0.067942
11       cpu_percent_mean_5s    0.063160
36        gpu_RC6_pct_std_5s    0.059424
6                gpu_RC6_pct    0.051698
43       gpu_VCS_pct_mean_5s    0.043163
37      gpu_RC6_pct_mean_30s    0.041586
44        gpu_VCS_pct_std_5s    0.040522
39       gpu_RCS_pct_mean_5s    0.035796
8                gpu_VCS_pct    0.030342
53          max_gpu_mean_30s    0.025754
52            max_gpu_std_5s    0.025191
49  gpu_Power_W_pkg_mean_30s    0.025067
7                gpu_RCS_pct    0.022189
Saving model to activity_model.joblib...
Done.

---

## 8. Final Outcomes
*   **Accuracy:** ~...% across test sets.
*   **Privacy:** The system classifies state without ever logging specific keystrokes or sensitive window titles in the production inference phase.
*   **Responsiveness:** Real-time state detection with a 1-second sampling rate.

### Future Work
*   Implementing **Hysteresis** to prevent "flickering" between states.
*   Expanding the model to support "Profiles" (e.g., Gamer vs. Programmer) to account for different baseline resource usages.
