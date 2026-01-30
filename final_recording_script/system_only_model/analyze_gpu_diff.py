import pandas as pd

# Load data
df = pd.read_csv('comprehensive_activity_log_with_Idle.csv')

# Filter for relevant columns and labels
cols = ['label', 'gpu_RC6_pct', 'gpu_RCS_pct', 'gpu_Power_W_pkg']
df_subset = df[cols]

# Group by label and calculate stats
stats = df_subset.groupby('label').agg(['mean', 'median', 'std', 'count'])

print(stats)
