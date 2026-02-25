import os
import sys
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
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

# 时间范围：过去两年
END_DATE = date.today() + timedelta(days=1)
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

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5


def parse_twitter_datetime(created_at_str: str) -> date:
    dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    return dt.date()


def generate_monthly_windows(start: date, end: date):
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
    cursor = ""
    page = 1
    window_total = 0
    max_pages = 200
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

        has_next = resp_json.get("has_next_page")
        next_cursor = resp_json.get("next_cursor")

        if not has_next or not next_cursor:
            break

        time.sleep(5.2)
        cursor = next_cursor
        page += 1

    return window_total


def load_existing_ids(csv_path):
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


def get_data_dir(user_name: str) -> str:
    """返回 data/<user_name>/ 目录路径，自动创建。"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data", user_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def fetch_all_tweets(user_name: str):
    headers = {"X-API-Key": API_KEY}

    data_dir = get_data_dir(user_name)
    output_csv = os.path.join(data_dir, "tweets.csv")

    windows = generate_monthly_windows(START_DATE, END_DATE)
    print(f"账号：{user_name}")
    print(f"时间范围：{START_DATE.isoformat()} ~ {END_DATE.isoformat()}")
    print(f"共拆分为 {len(windows)} 个月度窗口")
    print(f"输出：{output_csv}\n")

    seen_ids, covered_months = load_existing_ids(output_csv)
    if seen_ids:
        print(f"发现已有数据：{len(seen_ids)} 条推文，覆盖月份：{sorted(covered_months)}")

    total = len(seen_ids)

    file_exists = os.path.exists(output_csv) and len(seen_ids) > 0
    mode = "a" if file_exists else "w"

    with open(output_csv, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()

        for i, (since, until) in enumerate(windows, 1):
            window_month = since.strftime("%Y-%m")
            if window_month in covered_months:
                print(f"[窗口 {i}/{len(windows)}] {since.isoformat()} ~ {until.isoformat()} → 已覆盖，跳过")
                continue

            print(f"[窗口 {i}/{len(windows)}] {since.isoformat()} ~ {until.isoformat()}")
            window_count = fetch_window(writer, headers, user_name, since, until, seen_ids)
            f.flush()
            total += window_count
            print(f"  → 本窗口 {window_count} 条，累计 {total} 条\n")

            if i < len(windows):
                time.sleep(5.2)

    print(f"完成！总共 {total} 条 tweet 在 {output_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/scrape.py <username>")
        print("例如：python scripts/scrape.py usa912152217")
        sys.exit(1)

    username = sys.argv[1]
    fetch_all_tweets(username)
