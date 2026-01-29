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
loop {
open comprehensive_activity_log.csv | last
  | get app_id window_title
  | notify-send -t 1000 $"($in)"

  sleep 1sec
}
```
