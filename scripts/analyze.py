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
    kw_csv = os.path.join(data_dir, "top_keywords.csv")
    kw_df.to_csv(kw_csv, index=False, encoding="utf-8-sig")

    print(f"  Top 10 keywords (by tweet count):")
    for _, row in kw_df.head(10).iterrows():
        print(f"    {row['keyword']} ({row['english']}): {row['tweet_count']} tweets ({row['pct_of_tweets']}%)")
    print(f"  Saved {kw_csv}")


# ── 2. Posting Frequency ─────────────────────────────────────────────────────

def analyze_posting_frequency(df: pd.DataFrame, data_dir: str):
    print("\n── 2. Posting Frequency ──")

    # --- Monthly posting counts ---
    monthly_counts = df.groupby("month").size().reset_index(name="tweet_count").sort_values("month")
    monthly_csv = os.path.join(data_dir, "monthly_posting.csv")
    monthly_counts.to_csv(monthly_csv, index=False, encoding="utf-8-sig")

    print(f"  Total tweets: {len(df)}")
    print(f"  Months covered: {len(monthly_counts)}")
    print(f"  Avg per month: {len(df) / max(len(monthly_counts), 1):.0f}")
    most_active = monthly_counts.loc[monthly_counts["tweet_count"].idxmax()]
    print(f"  Most active month: {most_active['month']} ({most_active['tweet_count']} tweets)")
    print(f"  Saved {monthly_csv}")

    # --- Day-of-week × hour heatmap data ---
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap_data = df.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
    # Fill missing hours/days
    heatmap_data = heatmap_data.reindex(index=range(7), columns=range(24), fill_value=0)
    heatmap_data.index = day_labels
    heatmap_data.columns = [f"{h}:00" for h in range(24)]

    heatmap_csv = os.path.join(data_dir, "activity_heatmap.csv")
    heatmap_data.to_csv(heatmap_csv, encoding="utf-8-sig")
    print(f"  Saved {heatmap_csv}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_analysis(user_name: str):
    data_dir = get_data_dir(user_name)
    os.makedirs(data_dir, exist_ok=True)

    df = load_tweets(user_name)

    analyze_keywords(df, data_dir)
    analyze_posting_frequency(df, data_dir)

    print(f"\nAll analysis complete! Outputs in {data_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze.py <username>")
        print("Example: python scripts/analyze.py usa912152217")
        sys.exit(1)

    run_analysis(sys.argv[1])
