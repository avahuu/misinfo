# Twitter Misinformation Analysis

Ava's J-School thesis project analyzing misinformation on X (Twitter). [Visualization on Flourish →](https://public.flourish.studio/story/3480607/)

## Project Structure

```
├── scripts/
│   ├── scrape.py             # Scrape tweets from a user account
│   ├── clean.py              # Chinese text cleaning & keyword extraction
│   └── keyword_analysis.py   # Keyword frequency analysis
├── data/
│   └── <username>/           # Per-account data directory
│       ├── tweets.csv
│       ├── top_keywords.csv
│       └── ...
└── .env                      # API key (not tracked)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv python-dateutil pandas jieba
```

Add your [twitterapi.io](https://twitterapi.io) key to `.env`:
```
API_KEY=your_key_here
```

## Usage

All scripts take a Twitter username as an argument:

```bash
# 1. Scrape tweets (past 2 years, with resume support)
python -u scripts/scrape.py <username>

# 2. Clean text & extract top 50 Chinese keywords
python scripts/clean.py <username>

# 3. Keyword frequency analysis
python scripts/keyword_analysis.py <username>
```

Data is saved to `data/<username>/`.
