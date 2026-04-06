import os
import sys
import pandas as pd

def clean_for_flourish(user_name: str):
    """
    Reads daily_posting.csv and formats it to match the Flourish Calendar Heatmap template.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data", user_name)
    tl_dir = os.path.join(data_dir, "timeline")
    daily_csv = os.path.join(tl_dir, "daily_posting.csv")
    
    if not os.path.exists(daily_csv):
        print(f"Error: Could not find {daily_csv}")
        return

    # Load the daily aggregated data
    df = pd.read_csv(daily_csv)
    
    # Flourish Calendar Template expects a strict Date column (e.g., "5 September 2024")
    df["Date"] = pd.to_datetime(df["date"]).apply(lambda x: f"{x.day} {x.strftime('%B %Y')}")
    
    out_df = pd.DataFrame()
    out_df["Date"] = df["Date"]
    # We can provide a static Label/Account name to be used for "Filter by"
    out_df["Account"] = f"@{user_name}"
    # The metric to color by
    out_df["Tweet Count"] = df["tweet_count"]
    # Extra columns for popups
    out_df["Original"] = df["original_count"]
    out_df["Reply"] = df["reply_count"]
    
    # Save the reshaped dataframe
    out_name = os.path.join(tl_dir, "flourish_calendar.csv")
    out_df.to_csv(out_name, index=False, encoding="utf-8-sig")
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean.py <username>")
        print("Example: python scripts/clean.py usa912152217")
        sys.exit(1)
        
    user = sys.argv[1]
    clean_for_flourish(user)
