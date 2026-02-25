import os
import sys
import pandas as pd
import jieba
from collections import Counter
import re


def get_data_dir(user_name: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", user_name)


def clean_and_extract_keywords(user_name: str):
    data_dir = get_data_dir(user_name)
    tweets_csv = os.path.join(data_dir, "tweets.csv")

    if not os.path.exists(tweets_csv):
        print(f"Error: {tweets_csv} not found")
        sys.exit(1)

    # Load CSV
    df = pd.read_csv(tweets_csv)
    print(f"Loaded {len(df)} tweets from {tweets_csv}")

    # Merge all text
    all_text = df["text"].astype(str).str.cat(sep=" ")

    # Clean text
    all_text = re.sub(r"http\S+", "", all_text)       # Remove URLs
    all_text = re.sub(r"[a-zA-Z0-9]+", "", all_text)  # Remove English/numbers
    all_text = re.sub(r"[^\u4e00-\u9fa5]", " ", all_text)  # Keep only Chinese chars

    # Tokenize with jieba
    words = jieba.lcut(all_text)

    # Stopwords
    stopwords = set([
        "我们", "你们", "他们", "因为", "所以", "以及", "就是", "这个", "那个", "可以",
        "通过", "一个", "一些", "同时", "已经", "没有", "那么", "自己", "如果",
        "不过", "但是", "不是", "非常", "还有", "以及", "和",
    ])

    words = [w for w in words if len(w) >= 2 and w not in stopwords]

    counter = Counter(words)
    top50 = counter.most_common(50)

    # Print results
    print("===== Top 50 Chinese Keywords =====")
    for word, freq in top50:
        print(f"{word}: {freq}")

    # Save top keywords
    top_kw_csv = os.path.join(data_dir, "top_keywords.csv")
    pd.DataFrame(top50, columns=["keyword", "count"]).to_csv(top_kw_csv, index=False)
    print(f"\nKeywords saved to {top_kw_csv}")

    # Match keywords to tweets
    top_keywords = [kw for kw, _ in top50]

    def match_keywords(text: str):
        text = str(text)
        return [kw for kw in top_keywords if kw in text]

    df["matched_keywords"] = df["text"].astype(str).apply(match_keywords)

    tweets_kw_csv = os.path.join(data_dir, "tweets_with_keywords.csv")
    df.to_csv(tweets_kw_csv, index=False, encoding="utf-8-sig")
    print(f"Tweets with keywords saved to {tweets_kw_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean.py <username>")
        print("Example: python scripts/clean.py usa912152217")
        sys.exit(1)

    clean_and_extract_keywords(sys.argv[1])