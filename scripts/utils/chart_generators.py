# Chart Generator Functions
# Individual chart generation functions for the dissertation visualisation pipeline.
# Extracted from step7_visualizations.py for modularity.
# Each function produces one chart and saves it as a PNG file.

import os

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

# Default figure size and DPI for consistent output
FIGSIZE = (10, 6)
DPI = 150


# ─── RQ1: Sensitivity Analysis Charts ────────────────────────────────────────

def chart1_risk_vs_ads_scatter(df: pd.DataFrame, charts_dir: str):
    """Chart 1: RQ1 scatter plot of sensitive ratio vs ad status."""
    print("  01: Risk% vs Starting Ads (scatter)")

    fig, ax = plt.subplots(figsize=FIGSIZE)

    if 'ad_status' not in df.columns:
        print("      SKIP: No ad_status column")
        return

    plot_df = df[['sensitive_ratio', 'ad_status']].dropna()
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    colors = plot_df['ad_status'].map({'yes': '#2ecc71', 'no': '#e74c3c'})

    ax.scatter(plot_df['ad_status'].map({'yes': 1, 'no': 0}),
               plot_df['sensitive_ratio'],
               c=colors, alpha=0.7, s=100, edgecolors='white', linewidth=1)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_xlabel('Ad Status')
    ax.set_title('Risk % vs Ad Status')
    ax.axhline(y=2.0, color='orange', linestyle='--', alpha=0.7, label='T2 2%')
    ax.axhline(y=3.0, color='red', linestyle='--', alpha=0.7, label='T1 3%')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '01_risk_vs_ads_scatter.png'), dpi=DPI)
    plt.close()





# ─── RQ2: Perception Analysis Charts ─────────────────────────────────────────

def chart8_perception_categories(perception_df: pd.DataFrame, charts_dir: str):
    """Chart 8: RQ2 bar chart of viewer perception categories."""
    print("  08: Perception Categories (bar)")

    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)

    category_cols = [c for c in perception_df.columns if c.endswith('_mentions')]
    if not category_cols:
        print("      SKIP: No category columns found")
        return


# ─── RQ3: Algospeak Analysis Charts ──────────────────────────────────────────

def chart10_algospeak_transcript_vs_comments(algospeak_summary: pd.DataFrame, charts_dir: str):
    """Chart 10: RQ3 grouped bar comparing algospeak in transcripts vs comments."""
    print("  10: Algospeak Transcripts vs Comments (grouped bar)")

    if algospeak_summary is None or algospeak_summary.empty:
        print("      SKIP: No algospeak summary data")
        return

    if 'transcript_instances' not in algospeak_summary.columns:
        print("      SKIP: Missing required columns")
        return
