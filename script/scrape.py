import os
import csv
import time
from datetime import datetime, date

import requests
from dotenv import load_dotenv

# read api key
load_dotenv()
API_KEY = os.getenv("API_KEY")

# set constants
USER_NAME = "usa912152217"  # 西行小宝 2.0
BASE_URL = "https://api.twitterapi.io/twitter/user/last_tweets"

# cutoff date
CUTOFF_DATE = date(2020, 1, 1)

# csv fields
FIELDS = [
    "id",
    "createdAt",
    "text",
    "retweetCount",
    "replyCount",
    "likeCount",
    "quoteCount",
    "viewCount",
    "bookmarkCount",
]


def parse_twitter_datetime(created_at_str: str) -> date:
    """
    把 Twitter 的 createdAt:
      'Tue Dec 02 02:35:56 +0000 2025'
    转成 Python 的 date 对象（只比较日期）
    """
    dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    return dt.date()


def fetch_since_2020_to_csv(
    user_name: str,
    include_replies: bool = True,
    max_pages: int = 1000,
    output_csv: str = "tweets_usa912152217.csv",
):
    headers = {
        "X-API-Key": API_KEY
    }

    cursor = ""
    page = 1
    total = 0
    reached_old = False  # 是否已经遇到早于 CUTOFF_DATE 的 tweet

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        while page <= max_pages and not reached_old:
            params = {
                "userName": user_name,
                "cursor": cursor,
                "includeReplies": "true" if include_replies else "false",
            }

            print(f"Fetching page {page}, cursor={cursor!r} ...")
            res = requests.get(BASE_URL, headers=headers, params=params)
            print("Status:", res.status_code)

            # 免费版 QPS 限制：每 5 秒只能 1 个请求
            if res.status_code == 429:
                print("命中免费版限速（429），休息 6 秒后重试同一页 ...")
                time.sleep(6)
                continue

            if res.status_code != 200:
                print("请求失败：", res.text)
                break

            resp_json = res.json()

            # tweets 在 data 下面
            data_block = resp_json.get("data", {})
            tweets = data_block.get("tweets", [])

            if page == 1:
                print("top-level keys:", list(resp_json.keys()))
                print("data keys:", list(data_block.keys()))

            if not tweets:
                print("这一页没有 tweets 了，结束。")
                break

            for tw in tweets:
                created_at_str = tw.get("createdAt")
                if not created_at_str:
                    continue

                try:
                    created_date = parse_twitter_datetime(created_at_str)
                except Exception as e:
                    print("解析 createdAt 失败：", created_at_str, e)
                    continue

                # 从新到旧；一旦遇到比 CUTOFF_DATE 更早的，后面只会更旧
                if created_date >= CUTOFF_DATE:
                    row = {
                        "id": tw.get("id"),
                        "createdAt": created_at_str,
                        "text": tw.get("text"),
                        "retweetCount": tw.get("retweetCount"),
                        "replyCount": tw.get("replyCount"),
                        "likeCount": tw.get("likeCount"),
                        "quoteCount": tw.get("quoteCount"),
                        "viewCount": tw.get("viewCount"),
                        "bookmarkCount": tw.get("bookmarkCount"),
                    }
                    writer.writerow(row)
                    total += 1
                else:
                    print(
                        f"遇到早于 {CUTOFF_DATE.isoformat()} 的 tweet（{created_date.isoformat()}），停止继续翻页。"
                    )
                    reached_old = True
                    break

            print(f"当前累计写入 {total} 条（>= {CUTOFF_DATE.isoformat()}）")

            if reached_old:
                break

            # 分页信息在顶层
            has_next = resp_json.get("has_next_page")
            next_cursor = resp_json.get("next_cursor")

            print("has_next_page:", has_next, "next_cursor:", next_cursor)

            if not has_next or not next_cursor:
                print("has_next_page = false 或 next_cursor 为空，没有更多页面了。")
                break

            # ⚠ 免费版休眠时间
            print("Sleeping 5 秒以满足免费版 QPS 限制 ...")
            time.sleep(5.2)

            cursor = next_cursor
            page += 1

    print(f"完成！总共写入 {total} 条 tweet 到 {output_csv}")


if __name__ == "__main__":
    fetch_since_2020_to_csv(
        USER_NAME,
        include_replies=True,  
        max_pages=1000,
        output_csv=f"tweets_{USER_NAME}_since_2020-01-01.csv",
    )
