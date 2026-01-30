import pandas as pd
import matplotlib.pyplot as plt

# ======================
# Load data
# ======================
df = pd.read_csv("final_recording_script/comprehensive_activity_log_with_Idle.csv")

# Parse timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

# ======================
# Figure 1: CPU usage over time
# ======================
plt.figure(figsize=(12, 4))
plt.plot(df["timestamp"], df["cpu_percent"], linewidth=0.8)
plt.title("CPU usage over time (raw)")
plt.ylabel("CPU (%)")
plt.xlabel("Time")
plt.tight_layout()
plt.savefig("fig1_cpu_over_time.png")
plt.show()
plt.close()

# ======================
# Figure 2: Network and Disk activity
# ======================
plt.figure(figsize=(12, 4))
plt.plot(df["timestamp"], df["net_in_Bps"], label="Network In (Bps)", alpha=0.7)
plt.plot(df["timestamp"], df["disk_write_Bps"], label="Disk Write (Bps)", alpha=0.7)
plt.title("Network and Disk activity over time")
plt.ylabel("Bytes per second")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.savefig("fig2_network_disk.png")
plt.show()
plt.close()

# ======================
# Figure 3: GPU vs CPU (media signature)
# ======================
plt.figure(figsize=(12, 4))
plt.plot(df["timestamp"], df["gpu_RCS_pct"], label="GPU Render/Decode (%)")
plt.plot(df["timestamp"], df["cpu_percent"], label="CPU (%)", alpha=0.7)
plt.title("GPU vs CPU usage over time")
plt.ylabel("Usage (%)")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.savefig("fig3_gpu_vs_cpu.png")
plt.show()
plt.close()

# ======================
# Figure 4: Keyboard activity and idle time
# ======================
plt.figure(figsize=(12, 4))
plt.plot(df["timestamp"], df["keys_per_sec"], label="Keys per second")
plt.plot(df["timestamp"], df["idle_time_sec"], label="Idle time (sec)", alpha=0.7)
plt.title("Keyboard activity and idle time")
plt.ylabel("Value")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.savefig("fig4_keyboard_idle.png")
plt.show()
plt.close()

# ======================
# Figure 5: Multi-metric timeline (zoomed window)
# ======================
# take a small slice to show temporal patterns
sample = df.iloc[100:300]

plt.figure(figsize=(12, 5))
plt.plot(sample["timestamp"], sample["cpu_percent"], label="CPU (%)")
plt.plot(sample["timestamp"], sample["net_in_Bps"] / 1000, label="Net In (KBps)")
plt.plot(sample["timestamp"], sample["gpu_RCS_pct"], label="GPU (%)")
plt.title("Multi-metric timeline (zoomed window)")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.savefig("fig5_multimetric_window.png")
plt.show()
plt.close()

print("All figures generated successfully.")
