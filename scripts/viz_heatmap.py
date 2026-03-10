"""Generate a weekday × month heatmap from weekday_month_heatmap.csv."""
import os
import sys

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def main(user_name: str):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data", user_name)
    csv_path = os.path.join(data_dir, "weekday_month_heatmap.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run analyze.py --only posting first.")
        sys.exit(1)

    df = pd.read_csv(csv_path, index_col=0)

    fig, ax = plt.subplots(figsize=(max(len(df.columns) * 0.7, 12), 4))
    sns.heatmap(
        df,
        cmap="YlOrRd",
        ax=ax,
        linewidths=0.5,
        annot=True,
        fmt="d",
        cbar_kws={"label": "Tweet Count"},
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("")
    ax.set_title(f"Posting Frequency: Weekday × Month (@{user_name})")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    plt.tight_layout()

    out_path = os.path.join(data_dir, "weekday_month_heatmap.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/viz_heatmap.py <username>")
        sys.exit(1)

    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    main(sys.argv[1])
