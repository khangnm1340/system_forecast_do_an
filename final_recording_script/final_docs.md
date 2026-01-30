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
interactive_light (typing / browsing / reading)
interactive_heavy (coding, compiling)
media_playback
background_download

A study on the observability of human-computer interaction states through system resource telemetry.

UI rendering GPU differences(ghostty,chatgpt,telegram)

“This project investigates whether system resource telemetry alone can infer user activity states. Results show reliable detection of coarse-grained states (idle, media playback, heavy workload) while fine-grained interaction states remain difficult due to limited observability in resource metrics.”


metrics to keep
timestamp,cpu_percent,ram_percent,disk_read_Bps,disk_write_Bps,net_in_Bps,net_out_Bps,app_id(helium),window_title,keyboard_active,mouse_active,keys_per_sec,idle_time_sec,gpu


this is the script to print the selected parameter as a notification (for testing)
```sh
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
