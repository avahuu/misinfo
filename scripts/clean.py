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
        print(f"错误：找不到 {tweets_csv}")
        sys.exit(1)

    # --- load csv ---
    df = pd.read_csv(tweets_csv)
    print(f"加载 {len(df)} 条推文 from {tweets_csv}")

    # --- merge text ---
    all_text = df["text"].astype(str).str.cat(sep=" ")

    # --- clean ---
    all_text = re.sub(r"http\S+", "", all_text)
    all_text = re.sub(r"[a-zA-Z0-9]+", "", all_text)
    all_text = re.sub(r"[^\u4e00-\u9fa5]", " ", all_text)

    # --- 分词 ---
    words = jieba.lcut(all_text)

    # --- stopwords ---
    stopwords = set([
        "我们", "你们", "他们", "因为", "所以", "以及", "就是", "这个", "那个", "可以",
        "通过", "一个", "一些", "同时", "已经", "没有", "那么", "自己", "如果",
        "不过", "但是", "不是", "非常", "还有", "以及", "和",
    ])

    words = [w for w in words if len(w) >= 2 and w not in stopwords]

    counter = Counter(words)
    top50 = counter.most_common(50)

    # --- export ---
    print("===== Top 50 中文关键词 =====")
    for word, freq in top50:
        print(f"{word}: {freq}")

    # --- save ---
    top_kw_csv = os.path.join(data_dir, "top_keywords.csv")
    pd.DataFrame(top50, columns=["keyword", "count"]).to_csv(top_kw_csv, index=False)
    print(f"\n已保存关键词到 {top_kw_csv}")

    # --- match keywords to tweets ---
    top_keywords = [kw for kw, _ in top50]

    def match_keywords(text: str):
        text = str(text)
        return [kw for kw in top_keywords if kw in text]

    df["matched_keywords"] = df["text"].astype(str).apply(match_keywords)

    tweets_kw_csv = os.path.join(data_dir, "tweets_with_keywords.csv")
    df.to_csv(tweets_kw_csv, index=False, encoding="utf-8-sig")
    print(f"已保存带关键词的推文到 {tweets_kw_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/clean.py <username>")
        print("例如：python scripts/clean.py usa912152217")
        sys.exit(1)

    clean_and_extract_keywords(sys.argv[1])