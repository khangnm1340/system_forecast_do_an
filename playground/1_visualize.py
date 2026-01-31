import matplotlib
matplotlib.use("Agg")

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_theme(style="darkgrid")

def main(csv_path):
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    outdir = Path("plots")
    outdir.mkdir(exist_ok=True)

    # ---------- 1) System resource time series ----------
    plot_timeseries(df, 
        ["cpu_percent", "ram_percent"], 
        "CPU & RAM over time", outdir/"cpu_ram.png")

    plot_timeseries(df,
        ["disk_read_Bps", "disk_write_Bps"],
        "Disk IO over time", outdir/"disk_io.png")

    plot_timeseries(df,
        ["net_in_Bps", "net_out_Bps"],
        "Network IO over time", outdir/"net_io.png")

    # ---------- 2) Interaction signals ----------
    plot_timeseries(df,
        ["keyboard_active", "mouse_active", "true_focus"],
        "Binary interaction signals", outdir/"interaction_flags.png")

    plot_timeseries(df,
        ["avg_wpm", "instant_wpm", "keys_per_sec"],
        "Typing speed metrics", outdir/"typing_speeds.png")

    plot_timeseries(df,
        ["idle_time_sec", "focus_streak_sec"],
        "Idle time vs Focus streak", outdir/"idle_focus.png")

    plot_timeseries(df,
        ["window_switch_count"],
        "Window switching", outdir/"window_switch.png")

    # ---------- 3) Histograms ----------
    plot_hist(df["cpu_percent"], "CPU distribution", outdir/"hist_cpu.png")
    plot_hist(df["avg_wpm"], "Average WPM distribution", outdir/"hist_wpm.png")
    plot_hist(df["idle_time_sec"], "Idle time distribution", outdir/"hist_idle.png")

    # ---------- 4) Correlation heatmap ----------
    numeric_cols = df.select_dtypes(include="number")
    corr = numeric_cols.corr()
    plt.figure(figsize=(14,10))
    sns.heatmap(corr, cmap="coolwarm", center=0)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(outdir/"correlation_heatmap.png")
    plt.close()

    # ---------- 5) App usage timeline ----------
    plot_categorical_timeline(df, "app_name", outdir/"app_timeline.png")

    # ---------- 6) Focus vs CPU scatter ----------
    plt.figure(figsize=(8,6))
    sns.scatterplot(data=df, x="cpu_percent", y="focus_streak_sec", alpha=0.6)
    plt.title("CPU vs Focus streak")
    plt.tight_layout()
    plt.savefig(outdir/"cpu_vs_focus.png")
    plt.close()

    # ---------- 7) Typing burst vs WPM ----------
    plt.figure(figsize=(8,6))
    sns.scatterplot(data=df, x="typing_burst_sec", y="instant_wpm", alpha=0.6)
    plt.title("Typing burst vs Instant WPM")
    plt.tight_layout()
    plt.savefig(outdir/"burst_vs_wpm.png")
    plt.close()

    print(f"All plots saved in: {outdir.absolute()}")



def plot_timeseries(df, cols, title, outpath):
    plt.figure(figsize=(12,5))
    for c in cols:
        plt.plot(df["timestamp"], df[c], label=c)
    plt.legend()
    plt.title(title)
    plt.xlabel("Time")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_hist(series, title, outpath):
    plt.figure(figsize=(8,5))
    sns.histplot(series.dropna(), bins=50)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_categorical_timeline(df, col, outpath):
    plt.figure(figsize=(12,4))
    codes, uniques = pd.factorize(df[col])
    plt.plot(df["timestamp"], codes, drawstyle="steps-post")
    plt.yticks(range(len(uniques)), uniques)
    plt.title(f"{col} over time")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize.py data.csv")
        sys.exit(1)
    main(sys.argv[1])
