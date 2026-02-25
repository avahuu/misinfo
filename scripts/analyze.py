import os
import sys
import re
from collections import Counter
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import jieba
from snownlp import SnowNLP


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_data_dir(user_name: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", user_name)


def parse_dt(s):
    """Parse Twitter's createdAt string into a datetime."""
    return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")


def load_tweets(user_name: str) -> pd.DataFrame:
    data_dir = get_data_dir(user_name)
    csv_path = os.path.join(data_dir, "tweets.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    df["datetime"] = df["createdAt"].apply(parse_dt)
    df["date"] = df["datetime"].apply(lambda x: x.date())
    df["month"] = df["datetime"].apply(lambda x: x.strftime("%Y-%m"))
    df["weekday"] = df["datetime"].apply(lambda x: x.weekday())  # 0=Mon
    df["hour"] = df["datetime"].apply(lambda x: x.hour)

    # Ensure numeric columns
    for col in ["viewCount", "likeCount", "retweetCount", "replyCount", "quoteCount", "bookmarkCount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    print(f"Loaded {len(df)} tweets for @{user_name}")
    return df


# ── 1. Sentiment Analysis ────────────────────────────────────────────────────

def analyze_sentiment(df: pd.DataFrame, charts_dir: str):
    print("\n── Sentiment Analysis ──")

    def get_sentiment(text):
        text = str(text).strip()
        # Clean URLs and mentions
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"@\w+", "", text)
        if not text:
            return 0.5
        try:
            return SnowNLP(text).sentiments
        except Exception:
            return 0.5

    df["sentiment"] = df["text"].apply(get_sentiment)

    avg = df["sentiment"].mean()
    print(f"  Overall average sentiment: {avg:.3f} (0=negative, 1=positive)")

    # Monthly trend
    monthly = df.groupby("month")["sentiment"].mean().sort_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(len(monthly)), monthly.values, marker="o", linewidth=2, color="#4A90D9")
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5, label="Neutral (0.5)")
    ax.fill_between(range(len(monthly)), monthly.values, 0.5, alpha=0.15, color="#4A90D9")
    ax.set_xticks(range(len(monthly)))
    ax.set_xticklabels(monthly.index, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Avg Sentiment Score")
    ax.set_title("Monthly Sentiment Trend")
    ax.legend()
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, "sentiment_trend.png"), dpi=150)
    plt.close()
    print(f"  Saved sentiment_trend.png")

    return df


# ── 2. Keyword Frequency ─────────────────────────────────────────────────────

def analyze_keywords(df: pd.DataFrame, charts_dir: str, data_dir: str):
    print("\n── Keyword Frequency ──")

    all_text = df["text"].astype(str).str.cat(sep=" ")
    all_text = re.sub(r"http\S+", "", all_text)
    all_text = re.sub(r"[a-zA-Z0-9]+", "", all_text)
    all_text = re.sub(r"[^\u4e00-\u9fa5]", " ", all_text)

    words = jieba.lcut(all_text)

    stopwords = set([
        "我们", "你们", "他们", "因为", "所以", "以及", "就是", "这个", "那个", "可以",
        "通过", "一个", "一些", "同时", "已经", "没有", "那么", "自己", "如果",
        "不过", "但是", "不是", "非常", "还有", "以及", "和", "这些", "那些",
        "什么", "怎么", "为什么", "他的", "她的", "它的", "而且", "或者",
        "就像", "只是", "其实", "然后", "所有", "其他", "之后",
    ])

    words = [w for w in words if len(w) >= 2 and w not in stopwords]
    counter = Counter(words)
    top30 = counter.most_common(30)

    # Save to CSV
    kw_df = pd.DataFrame(top30, columns=["keyword", "count"])
    kw_df.to_csv(os.path.join(data_dir, "top_keywords.csv"), index=False)

    # Bar chart
    fig, ax = plt.subplots(figsize=(12, 7))
    keywords = [k for k, _ in top30]
    counts = [c for _, c in top30]
    bars = ax.barh(range(len(top30)), counts[::-1], color="#4A90D9")
    ax.set_yticks(range(len(top30)))
    ax.set_yticklabels(keywords[::-1], fontsize=10)
    ax.set_xlabel("Frequency")
    ax.set_title("Top 30 Keywords")
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, "top_keywords.png"), dpi=150)
    plt.close()

    print(f"  Top 10: {', '.join(f'{k}({c})' for k, c in top30[:10])}")
    print(f"  Saved top_keywords.png + top_keywords.csv")


# ── 3. Engagement Metrics ────────────────────────────────────────────────────

def analyze_engagement(df: pd.DataFrame, charts_dir: str, data_dir: str):
    print("\n── Engagement Metrics ──")

    metrics = ["viewCount", "likeCount", "retweetCount", "replyCount", "quoteCount", "bookmarkCount"]
    labels = ["Views", "Likes", "Retweets", "Replies", "Quotes", "Bookmarks"]

    # Summary stats
    stats = {}
    for m, l in zip(metrics, labels):
        stats[l] = {
            "mean": df[m].mean(),
            "median": df[m].median(),
            "max": df[m].max(),
            "total": df[m].sum(),
        }
        print(f"  {l}: mean={stats[l]['mean']:.0f}, median={stats[l]['median']:.0f}, max={stats[l]['max']}")

    stats_df = pd.DataFrame(stats).T
    stats_df.to_csv(os.path.join(data_dir, "engagement_stats.csv"))

    # Top 10 most-engaged tweets
    df["total_engagement"] = df["likeCount"] + df["retweetCount"] + df["replyCount"] + df["quoteCount"]
    top10 = df.nlargest(10, "total_engagement")[["createdAt", "text", "viewCount", "likeCount", "retweetCount", "replyCount", "total_engagement"]]
    top10["text"] = top10["text"].str[:100]  # Truncate for readability
    top10.to_csv(os.path.join(data_dir, "top_tweets.csv"), index=False, encoding="utf-8-sig")

    # Monthly engagement trend
    monthly = df.groupby("month")[["viewCount", "likeCount", "retweetCount"]].mean().sort_index()

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    colors = ["#4A90D9", "#E8534A", "#F5A623"]
    for ax, col, label, color in zip(axes, ["viewCount", "likeCount", "retweetCount"], ["Avg Views", "Avg Likes", "Avg Retweets"], colors):
        ax.plot(range(len(monthly)), monthly[col].values, marker="o", linewidth=2, color=color)
        ax.fill_between(range(len(monthly)), monthly[col].values, alpha=0.15, color=color)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)

    axes[-1].set_xticks(range(len(monthly)))
    axes[-1].set_xticklabels(monthly.index, rotation=45, ha="right", fontsize=9)
    axes[0].set_title("Monthly Engagement Trend")
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, "engagement_trend.png"), dpi=150)
    plt.close()
    print(f"  Saved engagement_trend.png + engagement_stats.csv + top_tweets.csv")


# ── 4. Posting Patterns ──────────────────────────────────────────────────────

def analyze_posting_patterns(df: pd.DataFrame, charts_dir: str):
    print("\n── Posting Patterns ──")

    # Monthly tweet count
    monthly_counts = df.groupby("month").size().sort_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(range(len(monthly_counts)), monthly_counts.values, color="#4A90D9", alpha=0.8)
    ax.set_xticks(range(len(monthly_counts)))
    ax.set_xticklabels(monthly_counts.index, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Number of Tweets")
    ax.set_title("Posting Frequency Over Time")
    for i, v in enumerate(monthly_counts.values):
        ax.text(i, v + 2, str(v), ha="center", fontsize=8, color="#333")
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, "posting_frequency.png"), dpi=150)
    plt.close()

    # Day-of-week × hour heatmap
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap_data = df.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
    # Fill missing hours/days
    heatmap_data = heatmap_data.reindex(index=range(7), columns=range(24), fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(heatmap_data, cmap="YlOrRd", ax=ax, linewidths=0.5,
                xticklabels=[f"{h}:00" for h in range(24)],
                yticklabels=day_labels)
    ax.set_xlabel("Hour (UTC)")
    ax.set_ylabel("Day of Week")
    ax.set_title("Posting Activity Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, "activity_heatmap.png"), dpi=150)
    plt.close()

    print(f"  Total tweets: {len(df)}")
    print(f"  Avg per month: {len(df) / max(len(monthly_counts), 1):.0f}")
    print(f"  Most active month: {monthly_counts.idxmax()} ({monthly_counts.max()} tweets)")
    print(f"  Saved posting_frequency.png + activity_heatmap.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_analysis(user_name: str):
    data_dir = get_data_dir(user_name)
    charts_dir = os.path.join(data_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    df = load_tweets(user_name)

    df = analyze_sentiment(df, charts_dir)
    analyze_keywords(df, charts_dir, data_dir)
    analyze_engagement(df, charts_dir, data_dir)
    analyze_posting_patterns(df, charts_dir)

    # Save full data with sentiment scores
    sentiment_csv = os.path.join(data_dir, "tweets_with_sentiment.csv")
    df[["id", "createdAt", "text", "sentiment", "viewCount", "likeCount",
        "retweetCount", "replyCount", "quoteCount", "bookmarkCount"]].to_csv(
        sentiment_csv, index=False, encoding="utf-8-sig"
    )
    print(f"\nAll analysis complete! Outputs in {data_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze.py <username>")
        print("Example: python scripts/analyze.py usa912152217")
        sys.exit(1)

    # Set font for Chinese characters
    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    run_analysis(sys.argv[1])
