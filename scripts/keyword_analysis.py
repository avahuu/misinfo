import os
import sys
import ast
import pandas as pd


def get_data_dir(user_name: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", user_name)


def analyze_keywords(user_name: str):
    data_dir = get_data_dir(user_name)
    tweets_kw_csv = os.path.join(data_dir, "tweets_with_keywords.csv")

    if not os.path.exists(tweets_kw_csv):
        print(f"错误：找不到 {tweets_kw_csv}")
        print("请先运行：python scripts/clean.py", user_name)
        sys.exit(1)

    df = pd.read_csv(tweets_kw_csv)
    print(f"加载 {len(df)} 条推文 from {tweets_kw_csv}")

    def safe_eval(x):
        try:
            return ast.literal_eval(x)
        except Exception:
            return []

    df["matched_keywords"] = df["matched_keywords"].apply(safe_eval)

    # 统计关键词 → 出现的 tweet 数
    keyword_tweet_count = {}
    for kws in df["matched_keywords"]:
        for kw in set(kws):
            keyword_tweet_count[kw] = keyword_tweet_count.get(kw, 0) + 1

    df_kw = pd.DataFrame(
        sorted(keyword_tweet_count.items(), key=lambda x: x[1], reverse=True),
        columns=["keyword", "tweet_count"],
    )

    output_csv = os.path.join(data_dir, "keyword_tweet_counts.csv")
    df_kw.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"已保存到 {output_csv}")
    print(df_kw.head(20).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/keyword_analysis.py <username>")
        print("例如：python scripts/keyword_analysis.py usa912152217")
        sys.exit(1)

    analyze_keywords(sys.argv[1])
