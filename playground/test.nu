timestamp
cpu_percent
ram_percent
disk_read_Bps
disk_write_Bps
net_in_Bps
net_out_Bps
window_id
app_id
pid
process_count

let key_mouse = [
keyboard_active,
mouse_active,
true_focus,
avg_wpm,
instant_wpm,
keys_per_sec,
typing_burst_sec,
idle_time_sec,
focus_streak_sec,
window_switch_count,
wpm_delta
]

open unified_activity_log.csv | select ...$key_mouse

hour
