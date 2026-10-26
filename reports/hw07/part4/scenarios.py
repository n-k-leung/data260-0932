import os
import sys
import pandas as pd
from agent import normalize_trips

SEED = 932
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")

source = sys.argv[1] if len(sys.argv) > 1 else "baywheels-tripdata.csv"
df, _ = normalize_trips(pd.read_csv(source))
df["minutes"] = df["duration_sec"] / 60

busiest = df["start_time"].str[:7].mode()[0]
month = df[df["start_time"].str.startswith(busiest)]
normal = month[month["minutes"].between(20, 44)].sample(540, random_state=SEED)
long_rides = month[month["minutes"].between(46, 90)].sample(60, random_state=SEED)
a = pd.concat([normal, long_rides]).sort_values("start_time")
b = df[df["minutes"] < 8].sample(500, random_state=SEED).copy()
starts = pd.Timestamp("2017-07-01 08:00:00") + pd.to_timedelta(range(0, 6 * 500, 6), unit="D")
b["start_time"] = starts.strftime("%Y-%m-%d %H:%M:%S")
if "end_time" in b.columns:
    b["end_time"] = (starts + pd.to_timedelta(b["duration_sec"].values, unit="s")).strftime(
        "%Y-%m-%d %H:%M:%S")

os.makedirs(RAW, exist_ok=True)
for name, data in [("scenario_membership_wins", a), ("scenario_payperuse_wins", b)]:
    data = data.drop(columns=["minutes"])
    data.to_csv(os.path.join(RAW, name + ".csv"), index=False)
    print(name, "rows:", len(data), "| first:", data["start_time"].min()[:10],
          "| last:", data["start_time"].max()[:10],
          "| months:", data["start_time"].str[:7].nunique(),
          "| average minutes:", round(data["duration_sec"].mean() / 60, 1))