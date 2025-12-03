import pandas as pd
import jieba
from collections import Counter
import re

# --- load csv ---
df = pd.read_csv("/Users/avahu/projects/twitter-scraper/data/tweets_usa912152217.csv")

# --- merge text ---
all_text = df["text"].astype(str).str.cat(sep=" ")

# --- clean ---
all_text = re.sub(r"http\S+", "", all_text)   # 去掉 URL
all_text = re.sub(r"[a-zA-Z0-9]+", "", all_text)  # 去掉英文/数字
all_text = re.sub(r"[^\u4e00-\u9fa5]", " ", all_text)  # 去掉非中文字符

# ---  ---
words = jieba.lcut(all_text)

# --- define stopwords ---
stopwords = set([
    "我们","你们","他们","因为","所以","以及","就是","这个","那个","可以",
    "通过","一个","一些","同时","已经","没有","那么","自己","如果",
    "不过","但是","不是","非常","还有","以及","和",
])

# 
words = [w for w in words if len(w) >= 2 and w not in stopwords]

# 
counter = Counter(words)
top50 = counter.most_common(50)

# --- export ---
print("===== Top 50 中文关键词 =====")
for word, freq in top50:
    print(f"{word}: {freq}")

# --- save to CSV ---
pd.DataFrame(top50, columns=["keyword", "count"]).to_csv("top_keywords.csv", index=False)
print("\n已保存关键词到 top_keywords.csv")

# 先取出关键词列表
top_keywords = [kw for kw, _ in top50]

def match_keywords(text: str):
    """
    返回这条 tweet 中出现的 top keywords 列表
    """
    text = str(text)
    return [kw for kw in top_keywords if kw in text]

# 在原 df 上新增一列 matched_keywords
df["matched_keywords"] = df["text"].astype(str).apply(match_keywords)

# save to CSV
df.to_csv("tweets_with_keywords.csv", index=False, encoding="utf-8-sig")