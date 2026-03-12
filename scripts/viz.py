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


# ── 3. Monthly Trends Bar Chart ────────────────────────────────────────────────

def viz_monthly_trends(user_name: str):
    data_dir = get_data_dir(user_name)
    csv_path = os.path.join(data_dir, "timeline", "monthly_posting.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df, x="month", y="tweet_count", color="#3498db", ax=ax)
    
    ax.set_title(f"Monthly Posting Trends (@{user_name})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Tweet Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = os.path.join(data_dir, "charts", "monthly_trends.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ── 4. Keyword Bubble Chart ───────────────────────────────────────────────────

def viz_keyword_bubbles(user_name: str):
    data_dir = get_data_dir(user_name)
    csv_path = os.path.join(data_dir, "post", "top_keywords.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path).head(30)
    
    # Simple "packed" bubble chart using scatter with random jitter
    # Real circle packing is complex, this provides the visual essence
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Normalize sizes for circles
    sizes = df["tweet_count"]
    sizes = (sizes / sizes.max()) * 3000
    
    # Generate random positions
    np.random.seed(42)
    x = np.random.rand(len(df))
    y = np.random.rand(len(df))
    
    scatter = ax.scatter(x, y, s=sizes, alpha=0.6, edgecolors="white", cmap="viridis", c=range(len(df)))
    
    for i, row in df.iterrows():
        label = f"{row['keyword']}\n({row['english']})"
        ax.text(x[i], y[i], label, ha='center', va='center', fontsize=8, fontweight='bold')

    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.axis('off')
    ax.set_title(f"Top Keywords - Tweet Volume (@{user_name})")
    
    plt.tight_layout()
    out_path = os.path.join(data_dir, "charts", "keyword_bubbles.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ── 5. Sentiment Bar Charts ───────────────────────────────────────────────────

def viz_sentiment(user_name: str):
    data_dir = get_data_dir(user_name)
    leaders_csv = os.path.join(data_dir, "sentiment", "leader_sentiment.csv")
    topics_csv = os.path.join(data_dir, "sentiment", "topic_sentiment.csv")

    if os.path.exists(leaders_csv):
        df = pd.read_csv(leaders_csv).dropna(subset=["avg_sentiment"])
        if len(df) > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            df = df.sort_values("avg_sentiment")
            colors = ["#e74c3c" if s < 0.5 else "#2ecc71" for s in df["avg_sentiment"]]
            sns.barplot(data=df, x="entity", y="avg_sentiment", palette=colors, ax=ax)
            ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
            ax.set_title(f"Sentiment Analysis by Leader (@{user_name})")
            ax.set_ylim(0, 1)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            out_path = os.path.join(data_dir, "charts", "sentiment_leaders.png")
            plt.savefig(out_path, dpi=150)
            plt.close()
            print(f"Saved {out_path}")

    if os.path.exists(topics_csv):
        df = pd.read_csv(topics_csv).dropna(subset=["avg_sentiment"])
        if len(df) > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            df = df.sort_values("avg_sentiment")
            colors = ["#e74c3c" if s < 0.5 else "#2ecc71" for s in df["avg_sentiment"]]
            sns.barplot(data=df, x="entity", y="avg_sentiment", palette=colors, ax=ax)
            ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
            ax.set_title(f"Sentiment Analysis by Topic (@{user_name})")
            ax.set_ylim(0, 1)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            out_path = os.path.join(data_dir, "charts", "sentiment_topics.png")
            plt.savefig(out_path, dpi=150)
            plt.close()
            print(f"Saved {out_path}")


# ── 6. Leader Sentiment Over Time ───────────────────────────────────────────

def viz_sentiment_trend(user_name: str):
    data_dir = get_data_dir(user_name)
    csv_path = os.path.join(data_dir, "sentiment", "sentiment_trend.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Find columns that end with _avg
    avg_cols = [c for c in df.columns if c.endswith("_avg")]
    for col in avg_cols:
        label = col.replace("_avg", "")
        ax.plot(df["month"], df[col], marker='o', label=label)
    
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.set_title(f"Leader Sentiment Trends Over Time (@{user_name})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg Sentiment Score")
    ax.set_ylim(0, 1)
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = os.path.join(data_dir, "charts", "sentiment_trends.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

CHARTS = {
    "heatmap": viz_heatmap,
    "burst": viz_burst_timeline,
    "trends": viz_monthly_trends,
    "bubbles": viz_keyword_bubbles,
    "sentiment": viz_sentiment,
    "sentiment_trend": viz_sentiment_trend,
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
