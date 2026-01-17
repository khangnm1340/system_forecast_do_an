# tasks
- [ ] Define what “system resources” you want to predict
timestamp,
cpu%, ram%,
disk_read, disk_write,
net_in, net_out,
active_window_class,
window_count,
keyboard_rate,
mouse_rate,
process_count
- [ ] Define what “user behavior” means
- [ ] Collect data
- [ ] Choose a baseline prediction method
- [ ] Train and evaluate
- [ ] make a nix module


## things to skip (or do only when time allows)
GPU, process name


# prompt to give AI
Forecasting system resource usage based on user behavior.
the plans are 

Define what “system resources” is ( CPU usage %, RAM usage, Disk I/O, Network bandwidth, GPU usage,)
Define what “user behavior” means
Application usage (which apps are opened,Keyboard/mouse activity, Window focus changes, Command history, Website visits, Time-of-day patterns,)
Collect data
Choose a baseline prediction method ("CPU usage 5 seconds ahead" as base)
Train and evaluate
Iterate

# notes
event11
## qualms about different patterns between users:
Train and test on same user.
Train on 3 users, test on unseen 4th.

# What I'm currently doing
make a python script to log the system
nix home manager git
getting uv to work on nix

