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

## Usage

```bash
# 1. Scrape tweets (past 2 years, with resume support)
python -u scripts/scrape.py <username>

# 2. Run all analyses
python scripts/analyze.py <username>

# 3. Run a single analysis
python scripts/analyze.py <username> --only keywords
python scripts/analyze.py <username> --only posting
python scripts/analyze.py <username> --only engagement
```

Data outputs are saved to `data/<username>/`.

## Scrape Methodology Notes

### Tweet types (`type` column)

Each tweet is classified as `original`, `reply`, or `retweet`:

- **Retweets** (`RT @...`): Detected by the `RT @username:` prefix that Twitter's API adds to retweet text. These are **excluded** from the final dataset because:
  - Their engagement metrics (views, likes, etc.) belong to the **original post**, not the retweeter
  - The Twitter search API inconsistently returns native reposts (the "repost" button), so RT coverage is unreliable
- **Replies**: For existing scraped data, replies are detected **heuristically** by checking if the tweet text starts with `@username`. This is approximate — future scrapes use the API's `isReply` field for accurate detection.
- **Original**: Everything else (the account's own tweets)

### What the search API returns

The scraper uses `from:<username>` search via twitterapi.io. This returns:
- ✅ Original tweets
- ✅ Replies
- ⚠️ Some retweets (with `RT @` prefix), but **not all** native reposts
- ❌ Native reposts (the repost button) are often missing from search results
