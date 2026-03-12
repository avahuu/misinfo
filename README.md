# Twitter Misinformation Analysis

Ava's J-School thesis project analyzing misinformation on X (Twitter). [Visualization on Flourish →](https://public.flourish.studio/story/3480607/)

## Project Structure

```
├── scripts/
│   ├── scrape.py             # Scrape tweets from a user account
│   └── analyze.py            # Keyword frequency, posting patterns & engagement trends
├── data/
│   └── <username>/           # Per-account data directory
│       ├── tweets.csv            # All scraped tweets
│       ├── top_keywords.csv      # Top 50 Chinese keywords with English translations
│       ├── monthly_posting.csv   # Monthly tweet counts
│       ├── activity_heatmap.csv  # Weekday × hour posting matrix
│       └── monthly_engagement.csv # Monthly avg views, likes, engagement
└── .env                      # API key (not tracked)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv python-dateutil pandas jieba deep-translator
```

Add your [twitterapi.io](https://twitterapi.io) key to `.env`:

```
API_KEY=your_key_here
```

## Analysis Features

### 1. Timeline

- **Activity Heatmap**: Weekday × hour/month posting matrix.
- **Burst Behavior**: Automatic detection of high-frequency posting sessions (e.g., 3+ tweets within 5-minute intervals).
- **Daily Volume**: Trends in tweet/reply volume over time.
- **Time Gaps**: Distribution of intervals between posts to identify automated or rapid-fire behavior.

### 2. Content

- **Monthly Trends**: Bar charts showing tweet volume shifts over time.
- **Keyword Analysis**:
  - Top 50 keywords by raw frequency and tweet percentage.
  - **Packed Bubble Chart**: Visual representation where circle area = tweet count.

### 3. Engagement (Top 10)\*\*: Rankings of posts by views, likes, and total engagement.

### 4. Sentiment Analysis

- **By Leader**: Sentiment scores for key figures (Trump, Biden etc.).
- **By Topics**: Sentiment analysis across specific themes (Immigration, Election, Media, etc.).
- **Sentiment Over Time**: Monthly tracking of sentiment trends for major political leaders.

---

## Viz

### Burst Behavior Timeline

Identifies rapid-fire posting sessions, highlighting potential bot-like or high-intensity activity.
![Burst Timeline](data/usa912152217/charts/burst_timeline.png)

### Activity Heatmap

Visualizes the rhythm of an account, showing which days and times are most active.
![Activity Heatmap](data/usa912152217/charts/weekday_month_heatmap.png)

---

## Scrape Methodology Notes

### Date range and incomplete months

The dataset covers **Feb 2024 – Jan 2026** (full months only). Partial months (e.g. Feb 2026) are dropped to avoid skewing monthly averages.

### Tweet types (`type` column)

Each tweet is classified as `original` or `reply`:

- **Retweets** (`RT @...`): Detected by the `RT @username:` prefix that Twitter's API adds to retweet text. These are **excluded** from the final dataset because:
  - Their engagement metrics (views, likes, etc.) belong to the **original post**, not the retweeter
  - The Twitter search API inconsistently returns native reposts (the "repost" button), so RT coverage is unreliable
- **Replies**: For existing scraped data, replies are detected **heuristically** by checking if the tweet text starts with `@username`. This is approximate — future scrapes use the API's `isReply` field for accurate detection.
- **Original**: Everything else (the account's own tweets)
