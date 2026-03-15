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


def chart2_risk_by_ads_boxplot(df: pd.DataFrame, charts_dir: str):
    """Chart 2: RQ1 box plot of sensitive ratio grouped by ad status."""
    print("  02: Risk% by Ad Status (box plot)")

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

    sns.boxplot(data=plot_df, x='ad_status', y='sensitive_ratio',
                order=['no', 'yes'], ax=ax)
    box_colors = ['#e74c3c', '#2ecc71']
    for patch, color in zip(ax.patches, box_colors):
        patch.set_facecolor(color)

    ax.set_xlabel('Ad Status')
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_title('Distribution of Risk % by Ad Status')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '02_risk_by_ads_boxplot.png'), dpi=DPI)
    plt.close()


def chart3_risk_vs_year_scatter(df: pd.DataFrame, charts_dir: str):
    """Chart 3: RQ1 scatter plot of sensitive ratio vs upload year."""
    print("  03: Risk% vs Upload Year (scatter)")

    fig, ax = plt.subplots(figsize=FIGSIZE)

    if 'published_at' not in df.columns:
        print("      SKIP: No published_at column")
        return

    plot_df = df[['sensitive_ratio', 'published_at']].dropna()
    plot_df['year'] = pd.to_datetime(plot_df['published_at'], errors='coerce').dt.year
    plot_df = plot_df.dropna(subset=['year'])

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    ax.scatter(plot_df['year'], plot_df['sensitive_ratio'],
               alpha=0.7, s=80, c='#3498db', edgecolors='white', linewidth=1)

    z = np.polyfit(plot_df['year'], plot_df['sensitive_ratio'], 1)
    p = np.poly1d(z)
    ax.plot(plot_df['year'].sort_values(), p(plot_df['year'].sort_values()),
            "r--", alpha=0.8, label='Trend line')

    ax.set_xlabel('Upload Year')
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_title('Risk % Over Time')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '03_risk_vs_year_scatter.png'), dpi=DPI)
    plt.close()


def chart4_avg_risk_by_ads_bar(df: pd.DataFrame, charts_dir: str):
    """Chart 4: RQ1 average sensitive ratio by ad status."""
    print("  04: Average Risk% by Ad Status (bar)")

    fig, ax = plt.subplots(figsize=(8, 6))

    if 'ad_status' not in df.columns:
        print("      SKIP: No ad_status column")
        return

    plot_df = df[['sensitive_ratio', 'ad_status']].dropna()
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    avg_risk = plot_df.groupby('ad_status')['sensitive_ratio'].mean()
    colors = ['#e74c3c' if idx == 'no' else '#2ecc71' for idx in avg_risk.index]
    bars = ax.bar(avg_risk.index, avg_risk.values, color=colors, edgecolor='white', linewidth=2)

    ax.set_xlabel('Ad Status')
    ax.set_ylabel('Average Sensitive Ratio (%)')
    ax.set_title('Average Risk % by Ad Status')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])

    for bar, val in zip(bars, avg_risk.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val:.2f}%', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '04_avg_risk_by_ads_bar.png'), dpi=DPI)
    plt.close()


def chart5_risk_vs_views_scatter(df: pd.DataFrame, charts_dir: str):
    """Chart 5: RQ1 scatter of views vs sensitive ratio with log scale."""
    print("  05: Risk% vs View Count (scatter)")

    fig, ax = plt.subplots(figsize=FIGSIZE)

    if 'view_count' not in df.columns:
        print("      SKIP: No view_count column")
        return

    plot_df = df[['sensitive_ratio', 'view_count']].dropna()
    plot_df = plot_df[plot_df['view_count'] > 0]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    ax.scatter(plot_df['view_count'], plot_df['sensitive_ratio'],
               alpha=0.7, s=80, c='#9b59b6', edgecolors='white', linewidth=1)

    ax.set_xscale('log')
    ax.set_xlabel('View Count (log scale)')
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_title('Risk % vs View Count')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '05_risk_vs_views_scatter.png'), dpi=DPI)
    plt.close()


def chart6_risk_histogram(df: pd.DataFrame, charts_dir: str):
    """Chart 6: RQ1 histogram of sensitive ratio distribution."""
    print("  06: Risk% Distribution (histogram)")

    fig, ax = plt.subplots(figsize=FIGSIZE)

    plot_df = df['sensitive_ratio'].dropna()

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    ax.hist(plot_df, bins=20, color='#3498db', edgecolor='white', alpha=0.8)
    ax.axvline(x=2.0, color='orange', linestyle='--', linewidth=2, label='T2 2%')
    ax.axvline(x=3.0, color='red', linestyle='--', linewidth=2, label='T1 3%')

    ax.set_xlabel('Sensitive Ratio (%)')
    ax.set_ylabel('Number of Videos')
    ax.set_title('Distribution of Risk %')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '06_risk_histogram.png'), dpi=DPI)
    plt.close()


def chart7_classification_pie(df: pd.DataFrame, charts_dir: str):
    """Chart 7: RQ1 pie chart of monetisation classification distribution."""
    print("  07: Classification Distribution (pie)")

    fig, ax = plt.subplots(figsize=(8, 8))

    if 'classification' not in df.columns:
        print("      SKIP: No classification column")
        return

    class_counts = df['classification'].value_counts()
    colors = {
        'Likely Monetised': '#2ecc71',
        'Uncertain': '#f39c12',
        'Likely Demonetised': '#e74c3c'
    }
    pie_colors = [colors.get(c, '#95a5a6') for c in class_counts.index]

    ax.pie(class_counts.values, labels=class_counts.index,
           colors=pie_colors, autopct='%1.1f%%',
           startangle=90, explode=[0.02]*len(class_counts))

    ax.set_title('Video Classification Distribution')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '07_classification_pie.png'), dpi=DPI)
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

    category_totals = {}
    for col in category_cols:
        category_name = col.replace('_mentions', '').replace('_', ' ').title()
        category_totals[category_name] = perception_df[col].sum()

    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_cats]
    values = [c[1] for c in sorted_cats]

    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(categories)))
    bars = ax.barh(categories, values, color=colors, edgecolor='white', linewidth=1)

    ax.set_xlabel('Number of Comments')
    ax.set_ylabel('Perception Category')
    ax.set_title('Perception Keywords by Category RQ2')

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{int(val)}', ha='left', va='center')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '08_perception_categories.png'), dpi=DPI)
    plt.close()


def chart9_top_videos_perception(perception_df: pd.DataFrame, charts_dir: str):
    """Chart 9: RQ2 bar chart of top videos by perception ratio."""
    print("  09: Top Videos by Perception Ratio (bar)")

    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return

    if 'perception_ratio' not in perception_df.columns:
        print("      SKIP: No perception_ratio column")
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)

    top_videos = perception_df.nlargest(10, 'perception_ratio')
    titles = top_videos['title'].apply(lambda x: x[:30] + '...' if len(str(x)) > 30 else x)

    colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(top_videos)))
    bars = ax.barh(range(len(top_videos)), top_videos['perception_ratio'], color=colors)

    ax.set_yticks(range(len(top_videos)))
    ax.set_yticklabels(titles)
    ax.set_xlabel('Perception Ratio (%)')
    ax.set_title('Top 10 Videos by Viewer Perception Comments')
    ax.invert_yaxis()

    for bar, val in zip(bars, top_videos['perception_ratio']):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}%', ha='left', va='center')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '09_top_videos_perception.png'), dpi=DPI)
    plt.close()


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

    fig, ax = plt.subplots(figsize=(12, 6))

    plot_df = algospeak_summary[algospeak_summary['total_instances'] > 0].head(15)

    if plot_df.empty:
        print("      SKIP: No algospeak found")
        return

    titles = plot_df['title'].apply(lambda x: x[:20] + '...' if len(str(x)) > 20 else x)
    x = np.arange(len(titles))
    width = 0.35

    ax.bar(x - width/2, plot_df['transcript_instances'], width,
           label='Transcripts', color='#3498db', edgecolor='white')
    ax.bar(x + width/2, plot_df['comment_instances'], width,
           label='Comments', color='#e74c3c', edgecolor='white')

    ax.set_xlabel('Video')
    ax.set_ylabel('Algospeak Instances')
    ax.set_title('Algospeak Creator Speech vs Viewer Comments RQ3')
    ax.set_xticks(x)
    ax.set_xticklabels(titles, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '10_algospeak_transcript_vs_comments.png'), dpi=DPI)
    plt.close()


def chart11_top_algospeak_terms(algospeak_df: pd.DataFrame, charts_dir: str):
    """Chart 11: RQ3 horizontal bar of top 15 algospeak terms."""
    print("  11: Top Algospeak Terms (horizontal bar)")

    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)

    term_counts = algospeak_df.groupby('algospeak_term')['occurrences'].sum()
    top_terms = term_counts.nlargest(15)

    if top_terms.empty:
        print("      SKIP: No terms found")
        return

    colors = plt.cm.plasma(np.linspace(0.2, 0.8, len(top_terms)))
    bars = ax.barh(range(len(top_terms)), top_terms.values, color=colors)

    ax.set_yticks(range(len(top_terms)))
    ax.set_yticklabels(top_terms.index)
    ax.set_xlabel('Total Occurrences')
    ax.set_title('Top 15 Algospeak Terms Used')
    ax.invert_yaxis()

    meanings = algospeak_df.drop_duplicates('algospeak_term').set_index('algospeak_term')['original_meaning']
    for i, (term, val) in enumerate(top_terms.items()):
        meaning = meanings.get(term, '')[:20]
        ax.text(val + 0.5, i, f'{int(val)} ({meaning})', ha='left', va='center')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '11_top_algospeak_terms.png'), dpi=DPI)
    plt.close()


def chart12_algospeak_by_category(algospeak_df: pd.DataFrame, charts_dir: str):
    """Chart 12: RQ3 pie chart of algospeak usage by category."""
    print("  12: Algospeak by Category (pie)")

    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return

    if 'category' not in algospeak_df.columns:
        print("      SKIP: No category column")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    category_counts = algospeak_df.groupby('category')['occurrences'].sum()
    category_counts = category_counts[category_counts > 0]

    if category_counts.empty:
        print("      SKIP: No categories found")
        return

    colors = plt.cm.Set3(np.linspace(0, 1, len(category_counts)))
    labels = [c.replace('_', ' ').title() for c in category_counts.index]

    ax.pie(category_counts.values, labels=labels,
           colors=colors, autopct='%1.1f%%',
           startangle=90, explode=[0.02]*len(category_counts))

    ax.set_title('Algospeak Usage by Category')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '12_algospeak_by_category.png'), dpi=DPI)
    plt.close()


# ─── Combined Insights ───────────────────────────────────────────────────────

def chart13_risk_vs_algospeak(main_df: pd.DataFrame, algospeak_summary: pd.DataFrame, charts_dir: str):
    """Chart 13: Combined scatter plot of risk% vs algospeak count."""
    print("  13: Risk% vs Algospeak Count (scatter)")

    if main_df is None or algospeak_summary is None:
        print("      SKIP: Missing data")
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)

    merged = main_df.merge(
        algospeak_summary[['video_id', 'total_instances']],
        on='video_id',
        how='left'
    )
    merged['total_instances'] = merged['total_instances'].fillna(0)

    if merged.empty:
        print("      SKIP: No data after merge")
        return

    ax.scatter(merged['sensitive_ratio'], merged['total_instances'],
               alpha=0.7, s=100, c='#1abc9c', edgecolors='white', linewidth=1)

    if len(merged) >= 3:
        z = np.polyfit(merged['sensitive_ratio'], merged['total_instances'], 1)
        p = np.poly1d(z)
        x_line = np.linspace(merged['sensitive_ratio'].min(), merged['sensitive_ratio'].max(), 100)
        ax.plot(x_line, p(x_line), "r--", alpha=0.8, label='Trend')

        corr = merged['sensitive_ratio'].corr(merged['total_instances'])
        ax.text(0.05, 0.95, f'Correlation: {corr:.2f}', transform=ax.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.set_xlabel('Sensitive Ratio (%)')
    ax.set_ylabel('Algospeak Instances')
    ax.set_title('Risk % vs Algospeak Usage')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '13_risk_vs_algospeak.png'), dpi=DPI)
    plt.close()


# ─── Category Analysis Charts ────────────────────────────────────────────────

def chart14_sensitivity_by_category(df: pd.DataFrame, charts_dir: str):
    """Chart 14: Sensitivity by Category — grouped bar monetised vs demonetised."""
    print("  14: Sensitivity by Category (grouped bar)")

    if df is None or df.empty:
        print("      SKIP: No sensitivity data")
        return

    cat_cols = [c for c in df.columns if c.endswith('_count') and c != 'sensitive_count'
                and c not in ('comment_count', 'like_count', 'view_count')]

    if not cat_cols or 'ad_status' not in df.columns:
        print("      SKIP: No category columns or ad_status")
        return

    plot_df = df[['ad_status'] + cat_cols].dropna(subset=['ad_status'])
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    means = plot_df.groupby('ad_status')[cat_cols].mean()
    categories = [c.replace('_count', '').replace('_', ' ').title() for c in cat_cols]

    x = np.arange(len(categories))
    width = 0.35

    if 'no' in means.index:
        ax.bar(x - width/2, means.loc['no'].values, width,
               label='No Ads (Demonetised)', color='#e74c3c', edgecolor='white')
    if 'yes' in means.index:
        ax.bar(x + width/2, means.loc['yes'].values, width,
               label='Has Ads (Monetised)', color='#2ecc71', edgecolor='white')

    ax.set_xlabel('Sensitive Word Category')
    ax.set_ylabel('Average Count per Video')
    ax.set_title('Sensitivity by Category: Monetised vs Demonetised')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '14_sensitivity_by_category.png'), dpi=DPI)
    plt.close()


def chart15_category_correlation_heatmap(category_df: pd.DataFrame, charts_dir: str):
    """Chart 15: Category Correlation Heatmap — sensitive vs algospeak categories."""
    print("  15: Category Correlation Heatmap")

    if category_df is None or category_df.empty:
        print("      SKIP: No category analysis data")
        return

    sw_cols = [c for c in category_df.columns if c.startswith('sw_') and c != 'sw_total']
    as_cols = [c for c in category_df.columns if c.startswith('as_') and c != 'as_total']

    if not sw_cols or not as_cols:
        print("      SKIP: No category columns found")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    corr_data = category_df[sw_cols + as_cols].corr()
    cross_corr = corr_data.loc[sw_cols, as_cols]

    sw_labels = [c.replace('sw_', '').replace('_', ' ').title() for c in sw_cols]
    as_labels = [c.replace('as_', '').replace('_', ' ').title() for c in as_cols]

    sns.heatmap(cross_corr.values, annot=True, fmt='.2f', cmap='RdYlGn',
                xticklabels=as_labels, yticklabels=sw_labels,
                center=0, vmin=-1, vmax=1, ax=ax)

    ax.set_title('Correlation: Sensitive Word Categories vs Algospeak Categories')
    ax.set_xlabel('Algospeak Category')
    ax.set_ylabel('Sensitive Word Category')

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '15_category_correlation_heatmap.png'), dpi=DPI)
    plt.close()
