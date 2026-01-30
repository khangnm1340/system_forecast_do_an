title + app_id + scroll_active + network_in = youtube watching

typing = when your keys per second exceeds a certain amount
do not log "Alt+1234" since those keys are for switching window

add window_title/app_name feature

train a simple model and only add more time where confusion is high

remove "hour" to prevent model from learning based on time

include gpu, use intel_gpu_top initially, then switched to reading from /sys/class/drm/card1/gt/gt0 to integrate with python script, currently scanning btop source code to see how they're doing it

made a script to print the current gpu usage(max of *_busy)

GPU rises when typing in terminal
GPU small rise when typing in ChatGPT or Telegram
GPU drops when UI static

realize can't know weather I'm typing or browsing, pivot to another state system

Define states differently:


idle
interactive_light (browsing / reading/ texting)
media_playback
interactive_heavy (coding,compiling code, playing games, training model)
background_download

A study on the observability of human-computer interaction states through system resource telemetry.

UI rendering GPU differences(ghostty,chatgpt,telegram)

“This project investigates whether system resource telemetry alone can infer user activity states. Results show reliable detection of coarse-grained states (idle, media playback, heavy workload) while fine-grained interaction states remain difficult due to limited observability in resource metrics.”


metrics to keep
timestamp,cpu_percent,ram_percent,disk_read_Bps,disk_write_Bps,net_in_Bps,net_out_Bps,app_id(helium),window_title,keyboard_active,mouse_active,keys_per_sec,idle_time_sec,gpu


this is the script to print the selected parameter as a notification (for testing)
```nu
let params = [cpu_percent ram_percent disk_write_Bps net_in_Bps max_gpu]

loop {
  open comprehensive_activity_log.csv
  | last
  | select ...$params
  | notify-send -t 1000 $"($in)"

  sleep 1sec
}
```

# calculate the variance , so that the model will learn

add behaviors so the model will learn

# manual state switching using a key for labeling
https://chatgpt.com/share/697bcb7c-e6bc-800f-889f-ad8a334350ec

Variance-based
std(cpu_percent)
std(gpu_RCS_pct)
std(net_in_Bps)

timed window implementation (https://chatgpt.com/share/697c3906-6360-800f-bd73-e1ff0c52ffae)
because individual rows are meaningless

# So if the raw labels are:

```
watch, watch, watch, idle, idle
```

The window label = `watch`

[1 2 3 4 5]: browsing
1 [2 3 4 5 6]: browsing
1 2 [3 4 5 6 7]: watching media
1 2 3 [4 5 6 7 8]: watching media
1 2 3 4 [5 6 7 8 9] : idle
1 2 3 4 5 [6 7 8 9 10] :idle
1 2 3 4 5 6 [7 8 9 10 11] : coding

# THE LABELING MECHANISM IS OFFICIALLY DONEEEEE

if no mouse or keyboard activity, fall back to idling


don't worry about the "idle state", you can set it later using "idle_time_sec"

added waybar module

different machines have different usage pattern, but overally, it's consistent

watching a movie too (so the model wouldn't just associate youtube with "media watching")

already test the correctness of labels


```nu
open comprehensive_activity_log.csv
| update label {|row|
    if $row.idle_time_sec > 10 and $row.label != "media_watching" {
        "Idle"
    } else {
        $row.label
    }
}
| save comprehensive_activity_log_with_Idle.csv
```


training results
❯ : uv run train_model.py
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
