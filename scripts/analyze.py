import os
import sys
import re
from collections import Counter
from datetime import datetime

import pandas as pd
import jieba
from deep_translator import GoogleTranslator


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


# ── 1. Keyword Frequency ─────────────────────────────────────────────────────

def analyze_keywords(df: pd.DataFrame, data_dir: str):
    print("\n── 1. Keyword Frequency ──")

    total_tweets = len(df)

    # First pass: get candidate keywords via jieba on all text
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
    # Get top 50 candidate keywords by raw frequency
    candidates = [kw for kw, _ in Counter(words).most_common(50)]

    # Second pass: count how many tweets contain each keyword
    keyword_stats = []
    for kw in candidates:
        tweet_count = df["text"].astype(str).str.contains(kw, na=False).sum()
        pct = tweet_count / total_tweets * 100
        keyword_stats.append({"keyword": kw, "tweet_count": tweet_count, "pct_of_tweets": round(pct, 1)})

    kw_df = pd.DataFrame(keyword_stats).sort_values("tweet_count", ascending=False).reset_index(drop=True)

    # Translate keywords to English
    print("  Translating keywords to English...")
    translator = GoogleTranslator(source="zh-CN", target="en")
    try:
        all_kws = kw_df["keyword"].tolist()
        # Batch translate by joining with newlines
        translated = translator.translate("\n".join(all_kws)).split("\n")
        if len(translated) == len(all_kws):
            kw_df["english"] = translated
        else:
            kw_df["english"] = [translator.translate(kw) for kw in all_kws]
    except Exception as e:
        print(f"  Translation failed ({e}), falling back to one-by-one...")
        kw_df["english"] = [translator.translate(kw) for kw in kw_df["keyword"]]

    # Export
    kw_csv = os.path.join(data_dir, "post", "top_keywords.csv")
    kw_df.to_csv(kw_csv, index=False, encoding="utf-8-sig")

    print(f"  Top 10 keywords (by tweet count):")
    for _, row in kw_df.head(10).iterrows():
        print(f"    {row['keyword']} ({row['english']}): {row['tweet_count']} tweets ({row['pct_of_tweets']}%)")
    print(f"  Saved {kw_csv}")


# ── 2. Posting Frequency ─────────────────────────────────────────────────────

def analyze_posting_frequency(df: pd.DataFrame, data_dir: str):
    print("\n── 2. Posting Frequency ──")

    tl = os.path.join(data_dir, "timeline")

    # --- Monthly posting counts ---
    monthly_counts = df.groupby("month").size().reset_index(name="tweet_count").sort_values("month")
    monthly_csv = os.path.join(tl, "monthly_posting.csv")
    monthly_counts.to_csv(monthly_csv, index=False, encoding="utf-8-sig")
    print(f"  Total tweets: {len(df)}")
    print(f"  Avg per month: {len(df) / max(len(monthly_counts), 1):.0f}")
    print(f"  Saved {monthly_csv}")

    # --- Weekday × month heatmap ---
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months_sorted = sorted(df["month"].unique())
    heatmap = df.groupby(["weekday", "month"]).size().unstack(fill_value=0)
    heatmap = heatmap.reindex(index=range(7), columns=months_sorted, fill_value=0)
    heatmap.index = day_labels

    heatmap_csv = os.path.join(tl, "weekday_month_heatmap.csv")
    heatmap.to_csv(heatmap_csv, encoding="utf-8-sig")
    print(f"  Saved {heatmap_csv}")


# ── 3. Engagement Trends ─────────────────────────────────────────────────────

def analyze_engagement(df: pd.DataFrame, data_dir: str):
    print("\n── 3. Engagement Trends ──")

    df["total_engagement"] = df["likeCount"] + df["retweetCount"] + df["replyCount"] + df["quoteCount"]

    metrics = ["viewCount", "likeCount", "retweetCount", "replyCount", "quoteCount", "bookmarkCount", "total_engagement"]
    monthly = df.groupby("month")[metrics].mean().sort_index().round(1)
    monthly.columns = ["avg_views", "avg_likes", "avg_retweets", "avg_replies", "avg_quotes", "avg_bookmarks", "avg_total_engagement"]

    engagement_csv = os.path.join(data_dir, "timeline", "monthly_engagement.csv")
    monthly.to_csv(engagement_csv, encoding="utf-8-sig")

    print(f"  Monthly engagement averages:")
    for _, row in monthly.iterrows():
        print(f"    {row.name}: views={row['avg_views']:.0f}, likes={row['avg_likes']:.0f}, engagement={row['avg_total_engagement']:.0f}")
    print(f"  Saved {engagement_csv}")


# ── 4. Posting Behavior ──────────────────────────────────────────────────────

def analyze_posting_behavior(df: pd.DataFrame, data_dir: str):
    print("\n── 4. Posting Behavior ──")

    df = df.copy()
    df["dt"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("dt")
    tl = os.path.join(data_dir, "timeline")

    # --- Daily posting volume (with inactive days filled as 0) ---
    active_daily = df.groupby(df["dt"].dt.date).agg(
        tweet_count=("id", "size"),
        original_count=("type", lambda x: (x == "original").sum()),
        reply_count=("type", lambda x: (x == "reply").sum()),
    ).reset_index()
    active_daily.columns = ["date", "tweet_count", "original_count", "reply_count"]

    # Fill all dates in range (including inactive days with 0)
    all_dates = pd.date_range(df["dt"].min().date(), df["dt"].max().date(), freq="D")
    full_daily = pd.DataFrame({"date": all_dates.date})
    full_daily = full_daily.merge(active_daily, on="date", how="left").fillna(0)
    for col in ["tweet_count", "original_count", "reply_count"]:
        full_daily[col] = full_daily[col].astype(int)

    daily_csv = os.path.join(tl, "daily_posting.csv")
    full_daily.to_csv(daily_csv, index=False, encoding="utf-8-sig")

    total_days = len(full_daily)
    active_days = (full_daily["tweet_count"] > 0).sum()
    inactive_days = total_days - active_days
    print(f"  Total days: {total_days}, active: {active_days} ({active_days/total_days*100:.1f}%), inactive: {inactive_days}")
    print(f"  Tweets per active day: mean={full_daily[full_daily['tweet_count']>0]['tweet_count'].mean():.1f}, max={full_daily['tweet_count'].max()}")
    print(f"  Saved {daily_csv}")

    # --- Time gap distribution (15 buckets) ---
    gaps_sec = df["dt"].diff().dt.total_seconds().dropna()

    buckets = [
        (0, 10, "0-10s"),
        (10, 20, "10-20s"),
        (20, 30, "20-30s"),
        (30, 60, "30s-1min"),
        (60, 120, "1-2min"),
        (120, 300, "2-5min"),
        (300, 600, "5-10min"),
        (600, 900, "10-15min"),
        (900, 1800, "15-30min"),
        (1800, 3600, "30min-1hr"),
        (3600, 7200, "1-2hr"),
        (7200, 14400, "2-4hr"),
        (14400, 28800, "4-8hr"),
        (28800, 43200, "8-12hr"),
        (43200, 86400, "12-24hr"),
        (86400, 259200, "1-3 days"),
        (259200, float("inf"), "3+ days"),
    ]

    dist_rows = []
    for lo, hi, label in buckets:
        count = ((gaps_sec >= lo) & (gaps_sec < hi)).sum()
        pct = count / len(gaps_sec) * 100
        dist_rows.append({"gap_range": label, "count": count, "pct": round(pct, 1)})

    dist_df = pd.DataFrame(dist_rows)
    dist_csv = os.path.join(tl, "time_gap_distribution.csv")
    dist_df.to_csv(dist_csv, index=False, encoding="utf-8-sig")

    print(f"  Median gap: {gaps_sec.median()/60:.1f} min")
    rapid = (gaps_sec < 60).sum()
    print(f"  Rapid-fire (<1 min): {rapid} ({rapid/len(gaps_sec)*100:.1f}%)")
    print(f"  Saved {dist_csv}")

    # --- Burst session detection ---
    # A burst = consecutive tweets with <5 min gaps; keep sessions with 3+ tweets
    BURST_GAP = 300  # 5 minutes
    MIN_BURST_SIZE = 3

    df = df.reset_index(drop=True)
    df["gap_sec"] = df["dt"].diff().dt.total_seconds()

    # Assign session IDs: new session starts when gap >= BURST_GAP
    session_id = 0
    sessions = []
    for i in range(len(df)):
        if i == 0 or df.loc[i, "gap_sec"] >= BURST_GAP:
            session_id += 1
        sessions.append(session_id)
    df["session_id"] = sessions

    # Aggregate per session
    burst_rows = []
    for sid, group in df.groupby("session_id"):
        if len(group) < MIN_BURST_SIZE:
            continue
        start = group["dt"].min()
        end = group["dt"].max()
        duration_sec = (end - start).total_seconds()
        avg_gap = duration_sec / (len(group) - 1) if len(group) > 1 else 0
        texts = group["text"].str[:60].tolist()

        burst_rows.append({
            "date": start.strftime("%Y-%m-%d"),
            "start_time": start.strftime("%H:%M:%S"),
            "end_time": end.strftime("%H:%M:%S"),
            "duration_min": round(duration_sec / 60, 1),
            "tweet_count": len(group),
            "avg_gap_sec": round(avg_gap, 1),
            "text_samples": " | ".join(texts[:5]),
        })

    burst_df = pd.DataFrame(burst_rows)
    burst_csv = os.path.join(tl, "burst_sessions.csv")
    burst_df.to_csv(burst_csv, index=False, encoding="utf-8-sig")

    # Summary stats
    summary = {
        "total_bursts": len(burst_df),
        "total_tweets_in_bursts": burst_df["tweet_count"].sum() if len(burst_df) else 0,
        "pct_tweets_in_bursts": round(burst_df["tweet_count"].sum() / len(df) * 100, 1) if len(burst_df) else 0,
        "avg_burst_size": round(burst_df["tweet_count"].mean(), 1) if len(burst_df) else 0,
        "max_burst_size": burst_df["tweet_count"].max() if len(burst_df) else 0,
        "avg_burst_duration_min": round(burst_df["duration_min"].mean(), 1) if len(burst_df) else 0,
    }
    summary_df = pd.DataFrame([summary])
    summary_csv = os.path.join(tl, "burst_summary.csv")
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")

    print(f"  Burst sessions (3+ tweets within 5 min gaps):")
    print(f"    Total bursts: {summary['total_bursts']}")
    print(f"    Tweets in bursts: {summary['total_tweets_in_bursts']} ({summary['pct_tweets_in_bursts']}% of all tweets)")
    print(f"    Avg burst size: {summary['avg_burst_size']} tweets, max: {summary['max_burst_size']}")
    print(f"  Saved {burst_csv} + {summary_csv}")


# ── Main ──────────────────────────────────────────────────────────────────────

ANALYSES = {
    "keywords": analyze_keywords,
    "posting": analyze_posting_frequency,
    "engagement": analyze_engagement,
    "behavior": analyze_posting_behavior,
}


def run_analysis(user_name: str, only: str | None = None):
    data_dir = get_data_dir(user_name)
    for sub in ["", "post", "timeline", "charts"]:
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)

    df = load_tweets(user_name)

    if only:
        if only not in ANALYSES:
            print(f"Error: unknown analysis '{only}'. Choose from: {', '.join(ANALYSES)}")
            sys.exit(1)
        ANALYSES[only](df, data_dir)
    else:
        for fn in ANALYSES.values():
            fn(df, data_dir)

    print(f"\nDone! Outputs in {data_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze.py <username> [--only keywords|posting|engagement]")
        print("Example: python scripts/analyze.py usa912152217 --only engagement")
        sys.exit(1)

    user = sys.argv[1]
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1]

    run_analysis(user, only)
