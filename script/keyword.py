import pandas as pd

df = pd.read_csv("tweets_with_keywords.csv")

# matched_keywords 
import ast

def safe_eval(x):
    try:
        return ast.literal_eval(x)
    except:
        return []

df["matched_keywords"] = df["matched_keywords"].apply(safe_eval)

# 统计关键词 → 出现的 tweet 数
keyword_tweet_count = {}

for kws in df["matched_keywords"]:
    for kw in set(kws):  # 用 set 去重，避免“同一关键词重复出现”导致统计错误
        keyword_tweet_count[kw] = keyword_tweet_count.get(kw, 0) + 1

# 转换为 dataframe
df_kw = pd.DataFrame(
    sorted(keyword_tweet_count.items(), key=lambda x: x[1], reverse=True),
    columns=["keyword", "tweet_count"]
)

# 保存
df_kw.to_csv("keyword_tweet_counts.csv", index=False, encoding="utf-8-sig")

