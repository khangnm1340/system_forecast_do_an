import pandas as pd

df = pd.read_csv("comprehensive_activity_log.csv")

df.loc[df["idle_time_sec"] > 10.0, "label"] = "Idle"
