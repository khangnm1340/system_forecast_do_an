import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import textwrap
import re

# Setup
INPUT_FILE = 'comprehensive_activity_log_with_Idle.csv'
OUTPUT_DIR = 'window_title_reports'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_text(text):
    """Remove emojis and non-ASCII characters that cause font warnings."""
    if not isinstance(text, str): return "Unknown"
    # Remove non-ascii
    text = text.encode("ascii", "ignore").decode("ascii")
    # Remove weird bracket isolates found in terminal titles
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()

def generate_window_visualizations():
    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 1. CLEAN DATA
    df['window_title'] = df['window_title'].apply(clean_text)
    
    # Identify Top 15 windows to keep the charts clean
    top_n = 15
    counts = df['window_title'].value_counts()
    top_windows = counts.nlargest(top_n).index
    
    # Group everything else into "Other"
    df['window_grouped'] = df['window_title'].apply(lambda x: x if x in top_windows else '... Other Windows ...')

    # 2. WINDOW FOCUS TIMELINE (Cleaned)
    print("Generating Window Focus Timeline (Top 15 + Others)...")
    plt.figure(figsize=(16, 10))
    
    # Sort y-axis so "Other" is at the bottom
    y_order = list(top_windows) + ['... Other Windows ...']
    
    sns.scatterplot(
        data=df, 
        x='timestamp', 
        y='window_grouped', 
        hue='label', 
        palette='viridis', 
        s=30, 
        edgecolor=None
    )
    
    plt.title(f'Timeline of Active Windows (Top {top_n} vs Others)')
    plt.yticks(ticks=range(len(y_order)), labels=[textwrap.fill(t, 50) for t in y_order])
    plt.xlabel('Time')
    plt.ylabel('Window Title')
    plt.legend(title='Activity Label', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/1_window_focus_timeline.png")
    plt.close()

    # 3. TOTAL DURATION (Fixed Palette Warning)
    print("Generating Window Duration Chart...")
    plt.figure(figsize=(12, 8))
    window_counts = df['window_grouped'].value_counts()
    
    sns.barplot(
        x=window_counts.values, 
        y=window_counts.index, 
        hue=window_counts.index,
        palette='magma',
        legend=False
    )
    
    plt.title('Time Spent per Window Group')
    plt.xlabel('Seconds')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/2_window_duration_ranking.png")
    plt.close()

    # 4. RESOURCE IMPACT (Fixed Palette Warning)
    print("Generating Resource Impact Boxplots...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    # CPU Usage
    sns.boxplot(
        data=df, 
        x='cpu_percent', 
        y='window_grouped', 
        ax=ax1, 
        hue='window_grouped',
        palette='Reds',
        legend=False
    )
    ax1.set_title('CPU % by Window')

    # GPU Usage
    sns.boxplot(
        data=df, 
        x='max_gpu', 
        y='window_grouped', 
        ax=ax2, 
        hue='window_grouped',
        palette='Blues',
        legend=False
    )
    ax2.set_title('GPU % by Window')

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/3_window_resource_impact.png")
    plt.close()

    # 5. BEHAVIOR HEATMAP
    print("Generating Behavior Heatmap...")
    # Calculate percentage of time each window spends in each label
    pivot_data = pd.crosstab(df['window_grouped'], df['label'], normalize='index') * 100
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot_data, annot=True, cmap="YlGnBu", fmt=".1f")
    plt.title('What activity state are you usually in per window? (%)')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/4_window_behavior_heatmap.png")
    plt.close()

    print(f"\nDone! Cleaned charts saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    try:
        generate_window_visualizations()
    except Exception as e:
        print(f"Error occurred: {e}")
