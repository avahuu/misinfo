import os
import csv
import time
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import requests
from dotenv import load_dotenv

# read api key
load_dotenv()
API_KEY = os.getenv("API_KEY")

# set constants
USER_NAME = "usa912152217"  # 西行小宝 2.0
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

# 时间范围：过去两年
END_DATE = date.today() + timedelta(days=1)  # 明天，确保今天的推文也被捕获
START_DATE = date(2024, 2, 24)

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

REQUEST_TIMEOUT = 30  # 每个请求最多等 30 秒
MAX_RETRIES = 5       # 同一页最多重试 5 次（429 或超时）


def parse_twitter_datetime(created_at_str: str) -> date:
    """
    把 Twitter 的 createdAt:
      'Tue Dec 02 02:35:56 +0000 2025'
    转成 Python 的 date 对象（只比较日期）
    """
    dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    return dt.date()


def generate_monthly_windows(start: date, end: date):
    """
    生成按月划分的时间窗口列表，每个窗口是 (since_date, until_date)。
    从最近的月份开始向过去遍历。
    """
    windows = []
    current_end = end
    while current_end > start:
        current_start = current_end - relativedelta(months=1)
        if current_start < start:
            current_start = start
        windows.append((current_start, current_end))
        current_end = current_start
    return windows


def fetch_window(writer, headers, user_name, since_date, until_date, seen_ids):
    """
    在一个时间窗口内按 cursor 翻页，抓取所有推文。
    返回本窗口写入的条数。
    """
    cursor = ""
    page = 1
    window_total = 0
    max_pages = 200  # 单窗口最大页数（安全阀）
    retries = 0

    query = f"from:{user_name} since:{since_date.isoformat()} until:{until_date.isoformat()}"

    while page <= max_pages:
        params = {
            "query": query,
            "queryType": "Latest",
            "cursor": cursor,
        }

        print(f"    第 {page} 页, cursor={cursor[:30]}{'...' if len(cursor) > 30 else ''}")

        try:
            res = requests.get(BASE_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            retries += 1
            print(f"    请求超时（第 {retries} 次重试）...")
            if retries >= MAX_RETRIES:
                print(f"    超过最大重试次数 {MAX_RETRIES}，跳过本窗口剩余部分")
                break
            time.sleep(6)
            continue
        except requests.exceptions.RequestException as e:
            retries += 1
            print(f"    网络异常：{e}（第 {retries} 次重试）...")
            if retries >= MAX_RETRIES:
                print(f"    超过最大重试次数 {MAX_RETRIES}，跳过本窗口剩余部分")
                break
            time.sleep(6)
            continue

        # 免费版 QPS 限制
        if res.status_code == 429:
            retries += 1
            print(f"    命中限速（429），第 {retries} 次重试，休息 6 秒...")
            if retries >= MAX_RETRIES:
                print(f"    超过最大重试次数 {MAX_RETRIES}，跳过本窗口剩余部分")
                break
            time.sleep(6)
            continue

        if res.status_code != 200:
            print(f"    请求失败（{res.status_code}）：{res.text}")
            break

        # 成功，重置重试计数
        retries = 0

        resp_json = res.json()
        tweets = resp_json.get("tweets", [])

        if not tweets:
            break

        for tw in tweets:
            tweet_id = tw.get("id")
            if not tweet_id or tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)

            row = {
                "id": tweet_id,
                "createdAt": tw.get("createdAt"),
                "text": tw.get("text"),
                "retweetCount": tw.get("retweetCount"),
                "replyCount": tw.get("replyCount"),
                "likeCount": tw.get("likeCount"),
                "quoteCount": tw.get("quoteCount"),
                "viewCount": tw.get("viewCount"),
                "bookmarkCount": tw.get("bookmarkCount"),
            }
            writer.writerow(row)
            window_total += 1

        # 分页
        has_next = resp_json.get("has_next_page")
        next_cursor = resp_json.get("next_cursor")

        if not has_next or not next_cursor:
            break

        # ⚠ 免费版休眠
        time.sleep(5.2)
        cursor = next_cursor
        page += 1

    return window_total


def load_existing_ids(csv_path):
    """读取已有 CSV，返回已抓取的 tweet ID 集合和已覆盖的月份集合。"""
    seen_ids = set()
    covered_months = set()
    if not os.path.exists(csv_path):
        return seen_ids, covered_months

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tweet_id = row.get("id")
            if tweet_id:
                seen_ids.add(tweet_id)
            created = row.get("createdAt")
            if created:
                try:
                    dt = parse_twitter_datetime(created)
                    covered_months.add(dt.strftime("%Y-%m"))
                except Exception:
                    pass

    return seen_ids, covered_months


def fetch_all_tweets(
    user_name: str,
    output_csv: str = "tweets_usa912152217.csv",
):
    headers = {"X-API-Key": API_KEY}

    windows = generate_monthly_windows(START_DATE, END_DATE)
    print(f"时间范围：{START_DATE.isoformat()} ~ {END_DATE.isoformat()}")
    print(f"共拆分为 {len(windows)} 个月度窗口")

    # 加载已有数据，支持断点续传
    seen_ids, covered_months = load_existing_ids(output_csv)
    if seen_ids:
        print(f"发现已有数据：{len(seen_ids)} 条推文，覆盖月份：{sorted(covered_months)}")

    total = len(seen_ids)

    # 用追加模式写入（如果文件已存在），或新建
    file_exists = os.path.exists(output_csv) and len(seen_ids) > 0
    mode = "a" if file_exists else "w"

    with open(output_csv, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()

        for i, (since, until) in enumerate(windows, 1):
            window_month = since.strftime("%Y-%m")
            # 跳过已完整覆盖的月份
            if window_month in covered_months:
                print(f"[窗口 {i}/{len(windows)}] {since.isoformat()} ~ {until.isoformat()} → 已覆盖，跳过")
                continue

            print(f"[窗口 {i}/{len(windows)}] {since.isoformat()} ~ {until.isoformat()}")
            window_count = fetch_window(writer, headers, user_name, since, until, seen_ids)
            f.flush()  # 每个窗口完成后刷新到磁盘
            total += window_count
            print(f"  → 本窗口 {window_count} 条，累计 {total} 条\n")

            # 窗口之间也休眠一下
            if i < len(windows):
                time.sleep(5.2)

    print(f"完成！总共 {total} 条 tweet 在 {output_csv}")


if __name__ == "__main__":
    fetch_all_tweets(
        USER_NAME,
        output_csv=f"tweets_{USER_NAME}_since_{START_DATE.isoformat()}.csv",
    )
