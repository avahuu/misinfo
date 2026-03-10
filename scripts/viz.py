"""Visualization scripts for tweet analysis data."""
import os
import sys

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np


def get_data_dir(user_name: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", user_name)


# ── 1. Weekday × Month Heatmap ───────────────────────────────────────────────

def viz_heatmap(user_name: str):
    data_dir = get_data_dir(user_name)
    csv_path = os.path.join(data_dir, "timeline", "weekday_month_heatmap.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run analyze.py --only posting first.")
        return

    df = pd.read_csv(csv_path, index_col=0)

    fig, ax = plt.subplots(figsize=(max(len(df.columns) * 0.7, 12), 4))
    sns.heatmap(
        df,
        cmap="YlOrRd",
        ax=ax,
        linewidths=0.5,
        annot=True,
        fmt="d",
        cbar_kws={"label": "Tweet Count"},
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("")
    ax.set_title(f"Posting Frequency: Weekday × Month (@{user_name})")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    plt.tight_layout()

    out_path = os.path.join(data_dir, "charts", "weekday_month_heatmap.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ── 2. Burst Timeline Scatter ────────────────────────────────────────────────

def viz_burst_timeline(user_name: str):
    data_dir = get_data_dir(user_name)
    tweets_path = os.path.join(data_dir, "tweets.csv")
    bursts_path = os.path.join(data_dir, "timeline", "burst_sessions.csv")

    if not os.path.exists(tweets_path):
        print(f"Error: {tweets_path} not found.")
        return
    if not os.path.exists(bursts_path):
        print(f"Error: {bursts_path} not found. Run analyze.py --only behavior first.")
        return

    # Load tweets
    df = pd.read_csv(tweets_path)
    df["dt"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("dt")

    # Load burst sessions to identify burst tweet times
    bursts = pd.read_csv(bursts_path)

    # Mark burst tweets: find tweets that fall within any burst window
    df["in_burst"] = False
    for _, b in bursts.iterrows():
        burst_start = pd.to_datetime(f"{b['date']} {b['start_time']}")
        burst_end = pd.to_datetime(f"{b['date']} {b['end_time']}") + pd.Timedelta(seconds=1)
        mask = (df["dt"] >= burst_start) & (df["dt"] <= burst_end)
        df.loc[mask, "in_burst"] = True

    # Plot: each tweet as a dot, x = date, y = hour of day
    fig, ax = plt.subplots(figsize=(18, 6))

    normal = df[~df["in_burst"]]
    burst = df[df["in_burst"]]

    ax.scatter(
        normal["dt"], normal["dt"].dt.hour + normal["dt"].dt.minute / 60,
        s=4, alpha=0.3, color="#888888", label=f"Normal ({len(normal)})", zorder=2,
    )
    ax.scatter(
        burst["dt"], burst["dt"].dt.hour + burst["dt"].dt.minute / 60,
        s=12, alpha=0.7, color="#E8534A", label=f"In burst ({len(burst)})", zorder=3,
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Hour of Day (UTC)")
    ax.set_title(f"Tweet Timeline — Burst Sessions Highlighted (@{user_name})")
    ax.set_yticks(range(0, 25, 2))
    ax.set_yticklabels([f"{h:02d}:00" for h in range(0, 25, 2)])
    ax.set_ylim(-0.5, 24.5)
    ax.invert_yaxis()
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.2)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = os.path.join(data_dir, "charts", "burst_timeline.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

CHARTS = {
    "heatmap": viz_heatmap,
    "burst": viz_burst_timeline,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python scripts/viz.py <username> [chart_name]")
        print(f"Charts: {', '.join(CHARTS)} (default: all)")
        sys.exit(1)

    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    user = sys.argv[1]
    chart = sys.argv[2] if len(sys.argv) > 2 else None

    if chart:
        if chart not in CHARTS:
            print(f"Unknown chart '{chart}'. Choose from: {', '.join(CHARTS)}")
            sys.exit(1)
        CHARTS[chart](user)
    else:
        for fn in CHARTS.values():
            fn(user)
