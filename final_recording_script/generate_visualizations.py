import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (15, 8)

OUTPUT_DIR = "activity_reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data(filepath):
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def plot_state_overlay(df):
    print("Generating 1_state_overlay.png...")
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)
    
    metrics = [
        ('cpu_percent', 'CPU Usage (%)', 'tab:blue'),
        ('ram_percent', 'RAM Usage (%)', 'tab:orange'),
        ('gpu_Power_W_pkg', 'GPU Power (W)', 'tab:green')
    ]
    
    # map labels to colors
    unique_labels = df['label'].unique()
    label_colors = {
        'idle': 'lightgray', 
        'interactive_light': '#d9f0a3', # light green-ish
        'media_watching': '#a6bddb',    # light blue-ish
        'gaming': '#fdae6b'             # light orange-ish
    }
    # fallback for unknown labels
    default_color = 'whitesmoke'

    for i, (col, title, color) in enumerate(metrics):
        ax = axes[i]
        ax.plot(df['timestamp'], df[col], label=title, color=color, linewidth=1)
        ax.set_ylabel(title)
        
        # Add colored background for states
        # Find segments
        df['label_change'] = df['label'].shift() != df['label']
        changes = df[df['label_change']].index.tolist()
        if 0 not in changes:
            changes.insert(0, 0)
        changes.append(len(df))
        
        for j in range(len(changes) - 1):
            start_idx = changes[j]
            end_idx = changes[j+1] - 1
            if end_idx >= len(df): end_idx = len(df) - 1
            
            segment_label = df.iloc[start_idx]['label']
            start_time = df.iloc[start_idx]['timestamp']
            end_time = df.iloc[end_idx]['timestamp']
            
            facecolor = label_colors.get(segment_label, default_color)
            ax.axvspan(start_time, end_time, facecolor=facecolor, alpha=0.3, linewidth=0)

    # Legend for states
    patches = [mpatches.Patch(color=color, label=label, alpha=0.3) 
               for label, color in label_colors.items() if label in unique_labels]
    fig.legend(handles=patches, loc='upper center', ncol=len(patches), title="Activity States")
    
    plt.xlabel("Time")
    plt.tight_layout(rect=[0, 0, 1, 0.95]) # make room for legend
    plt.savefig(f"{OUTPUT_DIR}/1_state_overlay.png")
    plt.close()

def plot_activity_swimlanes(df):
    print("Generating 2_activity_swimlanes.png...")
    fig, ax = plt.subplots(figsize=(15, 6))
    
    # 1. Keyboard
    # We treat 1 as active.
    # To make it performant, we find intervals where it is 1
    kb_active = df[df['keyboard_active'] == 1]
    if not kb_active.empty:
        # We plot as vertical broken bars or just a scatter/line
        # A Gantt style is better: horizontal bars
        # Finding contiguous segments
        kb_segments = []
        if len(kb_active) > 0:
            kb_df = df.copy()
            kb_df['group'] = (kb_df['keyboard_active'] != kb_df['keyboard_active'].shift()).cumsum()
            kb_groups = kb_df[kb_df['keyboard_active'] == 1].groupby('group')
            for _, group in kb_groups:
                start = group['timestamp'].iloc[0]
                end = group['timestamp'].iloc[-1]
                # if start == end, add a small duration
                if start == end:
                    end = start + pd.Timedelta(seconds=1)
                kb_segments.append((start, end - start))
        
        # Using broken_barh
        # ax.broken_barh(kb_segments, (20, 9), facecolors='tab:purple') # y=20, height=9
        # But broken_barh takes (x_start, width) in axis units. Time axis is tricky.
        # easier: hlines
        for start, duration in kb_segments:
             ax.hlines(y=3, xmin=start, xmax=start+duration, linewidth=10, color='tab:purple')

    # 2. Mouse
    mouse_active = df[df['mouse_active'] == 1]
    if not mouse_active.empty:
        m_df = df.copy()
        m_df['group'] = (m_df['mouse_active'] != m_df['mouse_active'].shift()).cumsum()
        m_groups = m_df[m_df['mouse_active'] == 1].groupby('group')
        for _, group in m_groups:
            start = group['timestamp'].iloc[0]
            end = group['timestamp'].iloc[-1]
            if start == end: end = start + pd.Timedelta(seconds=1)
            ax.hlines(y=2, xmin=start, xmax=end, linewidth=10, color='tab:cyan')

    # 3. App ID / Window
    # This is categorical. We'll map top N apps to colors, others to gray.
    # Segment by app_id
    df['app_change'] = df['app_id'].shift() != df['app_id']
    app_changes = df[df['app_change']].index.tolist()
    if 0 not in app_changes: app_changes.insert(0, 0)
    app_changes.append(len(df))
    
    # Get top 5 apps
    top_apps = df['app_id'].value_counts().nlargest(5).index.tolist()
    palette = sns.color_palette("husl", len(top_apps))
    app_colors = {app: palette[i] for i, app in enumerate(top_apps)}
    
    for j in range(len(app_changes) - 1):
        start_idx = app_changes[j]
        end_idx = app_changes[j+1] - 1
        if end_idx >= len(df): end_idx = len(df) - 1
        
        app_id = df.iloc[start_idx]['app_id']
        start_time = df.iloc[start_idx]['timestamp']
        end_time = df.iloc[end_idx]['timestamp']
        if start_time == end_time: end_time = start_time + pd.Timedelta(seconds=1)
        
        color = app_colors.get(app_id, 'lightgray')
        ax.hlines(y=1, xmin=start_time, xmax=end_time, linewidth=10, color=color)

    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(['App Focus', 'Mouse', 'Keyboard'])
    ax.set_xlabel('Time')
    
    # Legend for Apps
    patches = [mpatches.Patch(color=color, label=app.split('.')[-1]) # shorten name
               for app, color in app_colors.items()]
    patches.append(mpatches.Patch(color='lightgray', label='Other'))
    ax.legend(handles=patches, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=len(patches), title="Top Apps")
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/2_activity_swimlanes.png")
    plt.close()

def plot_distribution_by_label(df):
    print("Generating 3_distribution_by_label.png...")
    metrics = ['cpu_percent', 'gpu_Power_W_pkg', 'net_in_Bps']
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for i, col in enumerate(metrics):
        sns.violinplot(x='label', y=col, data=df, ax=axes[i], inner='quartile')
        axes[i].set_title(f"Distribution of {col}")
        axes[i].tick_params(axis='x', rotation=15)
        
        # Log scale for net_in_Bps if range is huge
        if col == 'net_in_Bps' and df[col].max() > 10000:
            axes[i].set_yscale('log')

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/3_distribution_by_label.png")
    plt.close()

def plot_throughput_mountain(df):
    print("Generating 4_throughput_mountain.png...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # Network (Top)
    ax1.fill_between(df['timestamp'], df['net_in_Bps'], color='tab:green', alpha=0.6, label='Net In')
    ax1.fill_between(df['timestamp'], -df['net_out_Bps'], color='tab:blue', alpha=0.6, label='Net Out')
    ax1.set_ylabel('Network Bytes/s (In/-Out)')
    ax1.legend(loc='upper right')
    ax1.axhline(0, color='black', linewidth=0.5)
    
    # Disk (Bottom, inverted)
    ax2.fill_between(df['timestamp'], df['disk_read_Bps'], color='tab:orange', alpha=0.6, label='Disk Read')
    ax2.fill_between(df['timestamp'], -df['disk_write_Bps'], color='tab:red', alpha=0.6, label='Disk Write')
    ax2.set_ylabel('Disk Bytes/s (Read/-Write)')
    ax2.legend(loc='upper right')
    ax2.axhline(0, color='black', linewidth=0.5)
    
    plt.xlabel('Time')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/4_throughput_mountain.png")
    plt.close()

def plot_correlation_heatmap(df):
    print("Generating 5_correlation_heatmap.png...")
    cols = ['keys_per_sec', 'cpu_percent', 'gpu_Power_W_pkg', 'net_in_Bps', 'gpu_RC6_pct', 'ram_percent']
    # Filter only numeric cols that exist
    valid_cols = [c for c in cols if c in df.columns]
    
    corr = df[valid_cols].corr()
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap='coolwarm', vmin=-1, vmax=1, center=0)
    plt.title('Feature Correlation Matrix')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/5_correlation_heatmap.png")
    plt.close()

def plot_small_multiples(df):
    print("Generating 6_small_multiples.png...")
    # Filter for top N apps to avoid too many plots
    top_apps = df['app_id'].value_counts().nlargest(9).index.tolist()
    subset = df[df['app_id'].isin(top_apps)].copy()
    
    # Simplify app names
    subset['app_name'] = subset['app_id'].apply(lambda x: x.split('.')[-1])
    
    g = sns.FacetGrid(subset, col="app_name", col_wrap=3, height=3, aspect=1.5, sharex=False)
    g.map(sns.lineplot, "timestamp", "cpu_percent", linewidth=1)
    
    # Improve date formatting on x-axis
    for ax in g.axes.flatten():
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.tick_params(axis='x', rotation=45)

    g.set_axis_labels("Time", "CPU %")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/6_small_multiples.png")
    plt.close()

def main():
    file_path = 'comprehensive_activity_log_with_Idle.csv'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print("Loading data...")
    df = load_data(file_path)
    print(f"Loaded {len(df)} records.")

    plot_state_overlay(df)
    plot_activity_swimlanes(df)
    plot_distribution_by_label(df)
    plot_throughput_mountain(df)
    plot_correlation_heatmap(df)
    plot_small_multiples(df)
    
    print(f"All visualizations saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
