# Project: Predicting User State Based on System Resources

**Topic:** Predicting User State Based on System Resources (formerly "Predicting System Usage")

## 1. Project Evolution & Motivation

### Phase 1: The "CPU Prediction" Trap
Initially, the goal was to predict current system usage (specifically CPU peaks) based on historical data (keyboard/mouse activity, command history, window titles, time of day). 

**The Obstacle:**
*   **Data Sparsity:** For 99.9% of tasks, system usage hovers predictably between 5-15%.
*   **Unpredictable Peaks:** Meaningful predictions (peaks) are heavily dependent on user intent (e.g., deciding to compile code or launch a game), which cannot be reliably forecasted by system history alone.

### Phase 2: Pivot to User State
The focus shifted from predicting *numbers* (CPU %) to predicting *states* (What is the user doing?). 
*   **Initial Labels:** Idle, Typing, Browsing.
*   **Issue:** Distinguishing "Typing" from "Browsing" proved nearly impossible using only system resource metrics (without invasive keylogging), as GPU/CPU signatures were too similar.

### Phase 3: The Current Approach
The current objective is to classify the **User State** using **only system resource metrics** (CPU, RAM, Disk, Network, GPU). This allows for a privacy-preserving model that does not require logging keystrokes or reading window titles in production.

**Target Labels:**
1.  **`idle`**: User is away.
2.  **`interactive_light`**: General usage (Coding, Browsing, Reading, Texting).
3.  **`media_playback`**: Watching videos (YouTube, Movies).

*Note: States like `interactive_heavy` (Gaming/Compiling) and `background_download` were excluded from the ML model as they can be detected via simple threshold rules (e.g., CPU > 80% or Net In > X Mbps).*

---

## 2. Methodology

### 2.1 Data Collection Strategy
The team (4 members using Arch Linux + Niri) collected data representing distinct user profiles.

*   **Metric Logging:**
    *   **CPU/RAM/Disk/Net:** via `psutil`.
    *   **GPU:** via `intel_gpu_top` (crucial for distinguishing video decoding from light rendering).
    *   **Window Info:** `niri msg -j active-window`.
    *   **Input Metrics:** `libinput debug-events` (used for "Typing Burst" and "WPM" calculations during analysis).

*   **Ground Truth Labeling:**
    Instead of rule-based labeling (which is error-prone), we adopted a **Manual-but-Correct** approach.
    *   **Mechanism:** Niri keyboard shortcuts are bound to write the current state to a file (`current_state.txt`).
    *   **Logging:** The data collection script reads this file every second to tag the metrics row.

![Screenshot: Visualization of raw data streams (CPU, GPU, Network) alongside the ground truth labels]

### 2.2 The "Idle" Detection Challenge
A major technical hurdle was distinguishing **Idle** from **Light Interactive** (e.g., reading a static web page) without input monitoring.
*   **Problem:** Both states show CPU ~1-3%.
*   **Solution:** **GPU Metrics**.
    *   `max_gpu`: The maximum usage of any single GPU engine proved to be the discriminator.
    *   *Idle:* `max_gpu` is often 0.0.
    *   *Reading:* Background browser compositing causes micro-spikes.

---

## 3. System Architecture

### 3.1 Data Flow
1.  **Collector (`10_comprehensive_activity_log.py`):** Runs as a daemon, sampling system metrics @ 1Hz.
2.  **Training (`train_model.py`):** Trains a Random Forest Classifier.
    *   Features: Rolling stats (Mean/Std Dev) over 5s and 30s windows.
    *   Weights: Heavy penalty (5.0) for missing `Idle` state.
3.  **Inference (`live_inference.py`):** Real-time prediction using the trained model + Heuristic overrides for reliability.

### 3.2 Key Scripts
*   **Verification Tool (Nushell):** A script used to verify log integrity via `notify-send`.
    ```nu
    #!/usr/bin/env nu
    # Define a command with arguments
    def main [
      ...params: string  # variadic arguments
    ] {
      if ($params | is-empty) {
        error make {
          msg: "You must provide at least one column name"
        }
      }

      loop {
        open comprehensive_activity_log.csv
        | last
        | select ...$params
        | notify-send -t 1000 $"($in)"

        sleep 1sec
      }
    }
    ```
*   **GPU Permissions:** 
    `sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top` (Allows non-sudo logging).

---

## 4. Modeling Tasks
We defined two modeling tasks to test generalization:

1.  **Task A — Personalized Model:** Train and test on the same user. Measures predictability of a single person.
2.  **Task B — Cross-User Model:** Train on 3 users, test on an unseen 4th. Measures generalization across behavior patterns.

![Screenshot: Confusion Matrix comparing Task A (Personalized) vs Task B (Cross-User) performance]

## 5. Visualizations & Reports
The project generates several visualizations to understand the data:
*   **State Overlay:** How predictions align with reality.
*   **Throughput Mountain:** Network usage vs System load.
*   **Window Focus Timeline:** App usage duration ranking.

![Screenshot: 'Throughput Mountain' visualization showing network usage]
![Screenshot: Activity Swimlanes showing state transitions over time]

---

## 6. Team & Setup
*   **Group Size:** 4 Members.
*   **OS:** Arch Linux.
*   **Window Manager:** Niri.
*   **Dataset:** ~58k+ lines of annotated logs (Mixed sources: Linux & Windows).
