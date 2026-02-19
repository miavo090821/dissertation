# Step 7: Generate Visualizations
# This script loads analysis results and produces 13 charts across RQ1, RQ2, RQ3 and combined insights
# It saves all charts into data/output/charts as PNG files
# Input files come from the final report and summary CSVs

import sys
import os
from datetime import datetime

# Add parent directory so config and utils can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import output directory settings and final report filename
    from config import DATA_OUTPUT_DIR, FINAL_REPORT_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

try:
    # Import data and plotting libraries
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing library - {e}")
    print("Run: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

# Set global chart style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Default figure size and DPI for consistent output
FIGSIZE = (10, 6)
DPI = 150


# Create chart directory if missing and return its path
def setup_chart_dir(base_dir: str) -> str:
    charts_dir = os.path.join(base_dir, DATA_OUTPUT_DIR, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir


# Load all datasets required for chart generation
def load_data(base_dir: str) -> dict:
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    data = {}
    
    # Load main analysis from Excel
    excel_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    if os.path.exists(excel_path):
        data['main'] = pd.read_excel(excel_path, sheet_name='Main Analysis')
    
    # Load perception analysis summary
    perception_path = os.path.join(output_dir, 'comments_perception_summary.csv')
    if os.path.exists(perception_path):
        data['perception'] = pd.read_csv(perception_path)
    
    # Load algospeak instance-level findings
    algospeak_path = os.path.join(output_dir, 'algospeak_findings.csv')
    if os.path.exists(algospeak_path):
        data['algospeak'] = pd.read_csv(algospeak_path)
    
    # Load algospeak aggregated summary
    algospeak_summary_path = os.path.join(output_dir, 'algospeak_findings_summary.csv')
    if os.path.exists(algospeak_summary_path):
        data['algospeak_summary'] = pd.read_csv(algospeak_summary_path)
    
    return data


# Chart 1 RQ1 scatter plot of sensitive ratio vs starting advertisement status
def chart1_risk_vs_ads_scatter(df: pd.DataFrame, charts_dir: str):
    print("  01: Risk% vs Starting Ads (scatter)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Check for ad_status column
    if 'ad_status' not in df.columns:
        print("      SKIP: No ad_status column")
        return

    # Clean dataset
    plot_df = df[['sensitive_ratio', 'ad_status']].dropna()
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    # Colour mapping
    colors = plot_df['ad_status'].map({'yes': '#2ecc71', 'no': '#e74c3c'})

    # Scatter plot
    ax.scatter(plot_df['ad_status'].map({'yes': 1, 'no': 0}),
               plot_df['sensitive_ratio'],
               c=colors, alpha=0.7, s=100, edgecolors='white', linewidth=1)

    # Labels and formatting
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_xlabel('Ad Status')
    ax.set_title('Risk % vs Ad Status')
    
    # Add threshold lines
    ax.axhline(y=2.0, color='orange', linestyle='--', alpha=0.7, label='T2 2%')
    ax.axhline(y=3.0, color='red', linestyle='--', alpha=0.7, label='T1 3%')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '01_risk_vs_ads_scatter.png'), dpi=DPI)
    plt.close()


# Chart 2 RQ1 box plot of sensitive ratio grouped by ad status
def chart2_risk_by_ads_boxplot(df: pd.DataFrame, charts_dir: str):
    print("  02: Risk% by Ad Status (box plot)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Check for ad_status column
    if 'ad_status' not in df.columns:
        print("      SKIP: No ad_status column")
        return

    # Clean dataset
    plot_df = df[['sensitive_ratio', 'ad_status']].dropna()
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    # Draw boxplot
    sns.boxplot(data=plot_df, x='ad_status', y='sensitive_ratio',
                order=['no', 'yes'], ax=ax)
    # Manually color boxes to match charts 1 & 4
    box_colors = ['#e74c3c', '#2ecc71']  # red=no, green=yes
    for patch, color in zip(ax.patches, box_colors):
        patch.set_facecolor(color)

    # Labels
    ax.set_xlabel('Ad Status')
    ax.set_ylabel('Sensitive Ratio (%)')
    ax.set_title('Distribution of Risk % by Ad Status')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])

    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '02_risk_by_ads_boxplot.png'), dpi=DPI)
    plt.close()


# Chart 3 RQ1 scatter plot of sensitive ratio vs upload year
def chart3_risk_vs_year_scatter(df: pd.DataFrame, charts_dir: str):
    print("  03: Risk% vs Upload Year (scatter)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    if 'published_at' not in df.columns:
        print("      SKIP: No published_at column")
        return
    
    # Extract year from date
    plot_df = df[['sensitive_ratio', 'published_at']].dropna()
    plot_df['year'] = pd.to_datetime(plot_df['published_at'], errors='coerce').dt.year
    plot_df = plot_df.dropna(subset=['year'])
    
    if plot_df.empty:
        print("      SKIP: No valid data")
        return
    
    # Scatter plot
    ax.scatter(plot_df['year'], plot_df['sensitive_ratio'],
               alpha=0.7, s=80, c='#3498db', edgecolors='white', linewidth=1)

    # Add trend line
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


# Chart 4 RQ1 average sensitive ratio by ad status
def chart4_avg_risk_by_ads_bar(df: pd.DataFrame, charts_dir: str):
    print("  04: Average Risk% by Ad Status (bar)")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Check for ad_status column
    if 'ad_status' not in df.columns:
        print("      SKIP: No ad_status column")
        return

    # Clean dataset
    plot_df = df[['sensitive_ratio', 'ad_status']].dropna()
    plot_df['ad_status'] = plot_df['ad_status'].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df['ad_status'].isin(['yes', 'no'])]

    if plot_df.empty:
        print("      SKIP: No valid data")
        return

    # Compute mean values
    avg_risk = plot_df.groupby('ad_status')['sensitive_ratio'].mean()

    # Colour mapping
    colors = ['#e74c3c' if idx == 'no' else '#2ecc71' for idx in avg_risk.index]
    bars = ax.bar(avg_risk.index, avg_risk.values, color=colors, edgecolor='white', linewidth=2)

    ax.set_xlabel('Ad Status')
    ax.set_ylabel('Average Sensitive Ratio (%)')
    ax.set_title('Average Risk % by Ad Status')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])
    
    # Label each bar
    for bar, val in zip(bars, avg_risk.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val:.2f}%', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '04_avg_risk_by_ads_bar.png'), dpi=DPI)
    plt.close()


# Chart 5 RQ1 scatter of views vs sensitive ratio with log scale
def chart5_risk_vs_views_scatter(df: pd.DataFrame, charts_dir: str):
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


# Chart 6 RQ1 histogram of sensitive ratio distribution
def chart6_risk_histogram(df: pd.DataFrame, charts_dir: str):
    print("  06: Risk% Distribution (histogram)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    plot_df = df['sensitive_ratio'].dropna()
    
    if plot_df.empty:
        print("      SKIP: No valid data")
        return
    
    ax.hist(plot_df, bins=20, color='#3498db', edgecolor='white', alpha=0.8)
    
    # Add thresholds
    ax.axvline(x=2.0, color='orange', linestyle='--', linewidth=2, label='T2 2%')
    ax.axvline(x=3.0, color='red', linestyle='--', linewidth=2, label='T1 3%')
    
    ax.set_xlabel('Sensitive Ratio (%)')
    ax.set_ylabel('Number of Videos')
    ax.set_title('Distribution of Risk %')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '06_risk_histogram.png'), dpi=DPI)
    plt.close()


# Chart 7 RQ1 pie chart of monetisation classification distribution
def chart7_classification_pie(df: pd.DataFrame, charts_dir: str):
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


# Chart 8 RQ2 bar chart of viewer perception categories aggregated across comments
def chart8_perception_categories(perception_df: pd.DataFrame, charts_dir: str):
    print("  08: Perception Categories (bar)")
    
    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Category detection
    category_cols = [c for c in perception_df.columns if c.endswith('_mentions')]
    
    if not category_cols:
        print("      SKIP: No category columns found")
        return
    
    # Sum mentions per category
    category_totals = {}
    for col in category_cols:
        category_name = col.replace('_mentions', '').replace('_', ' ').title()
        category_totals[category_name] = perception_df[col].sum()
    
    # Sort descending
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_cats]
    values = [c[1] for c in sorted_cats]
    
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(categories)))
    bars = ax.barh(categories, values, color=colors, edgecolor='white', linewidth=1)
    
    ax.set_xlabel('Number of Comments')
    ax.set_ylabel('Perception Category')
    ax.set_title('Perception Keywords by Category RQ2')
    
    # Add labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{int(val)}', ha='left', va='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '08_perception_categories.png'), dpi=DPI)
    plt.close()


# Chart 9 RQ2 bar chart of top videos by perception ratio
def chart9_top_videos_perception(perception_df: pd.DataFrame, charts_dir: str):
    print("  09: Top Videos by Perception Ratio (bar)")
    
    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return
    
    if 'perception_ratio' not in perception_df.columns:
        print("      SKIP: No perception_ratio column")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Top 10 videos
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


# Chart 10 RQ3 grouped bar chart comparing algospeak in transcripts versus viewer comments
def chart10_algospeak_transcript_vs_comments(algospeak_summary: pd.DataFrame, charts_dir: str):
    print("  10: Algospeak Transcripts vs Comments (grouped bar)")
    
    if algospeak_summary is None or algospeak_summary.empty:
        print("      SKIP: No algospeak summary data")
        return
    
    if 'transcript_instances' not in algospeak_summary.columns:
        print("      SKIP: Missing required columns")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Select videos with at least one algospeak instance
    plot_df = algospeak_summary[algospeak_summary['total_instances'] > 0].head(15)
    
    if plot_df.empty:
        print("      SKIP: No algospeak found")
        return
    
    titles = plot_df['title'].apply(lambda x: x[:20] + '...' if len(str(x)) > 20 else x)
    x = np.arange(len(titles))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, plot_df['transcript_instances'], width, 
                   label='Transcripts', color='#3498db', edgecolor='white')
    bars2 = ax.bar(x + width/2, plot_df['comment_instances'], width, 
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


# Chart 11 RQ3 horizontal bar chart of top 15 algospeak terms and meanings
def chart11_top_algospeak_terms(algospeak_df: pd.DataFrame, charts_dir: str):
    print("  11: Top Algospeak Terms (horizontal bar)")
    
    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Count usage across all videos
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
    
    # Extract meanings for display
    meanings = algospeak_df.drop_duplicates('algospeak_term').set_index('algospeak_term')['original_meaning']
    for i, (term, val) in enumerate(top_terms.items()):
        meaning = meanings.get(term, '')[:20]
        ax.text(val + 0.5, i, f'{int(val)} ({meaning})', ha='left', va='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '11_top_algospeak_terms.png'), dpi=DPI)
    plt.close()


# Chart 12 RQ3 pie chart of algospeak usage by category
def chart12_algospeak_by_category(algospeak_df: pd.DataFrame, charts_dir: str):
    print("  12: Algospeak by Category (pie)")
    
    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return
    
    if 'category' not in algospeak_df.columns:
        print("      SKIP: No category column")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Count total occurrences by category
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


# Chart 13 Combined analysis scatter plot measuring relationship between sensitive ratio and algospeak usage
def chart13_risk_vs_algospeak(main_df: pd.DataFrame, algospeak_summary: pd.DataFrame, charts_dir: str):
    print("  13: Risk% vs Algospeak Count (scatter)")
    
    if main_df is None or algospeak_summary is None:
        print("      SKIP: Missing data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Merge datasets by video_id
    merged = main_df.merge(
        algospeak_summary[['video_id', 'total_instances']], 
        on='video_id', 
        how='left'
    )
    merged['total_instances'] = merged['total_instances'].fillna(0)
    
    if merged.empty:
        print("      SKIP: No data after merge")
        return
    
    # Scatter plot
    ax.scatter(merged['sensitive_ratio'], merged['total_instances'],
               alpha=0.7, s=100, c='#1abc9c', edgecolors='white', linewidth=1)
    
    # Trend line and correlation
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


# Main execution function
def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    charts_dir = setup_chart_dir(base_dir)
    
    print("=" * 70)
    print("STEP 7: GENERATE VISUALIZATIONS")
    print("=" * 70)
    
    # Load all datasets
    print("\nLoading data...")
    data = load_data(base_dir)
    
    main_df = data.get('main')
    perception_df = data.get('perception')
    algospeak_df = data.get('algospeak')
    algospeak_summary = data.get('algospeak_summary')
    
    # Print loaded dataset sizes
    if main_df is not None:
        print(f"  Main analysis: {len(main_df)} videos")
    if perception_df is not None:
        print(f"  Perception data: {len(perception_df)} videos")
    if algospeak_df is not None:
        print(f"  Algospeak findings: {len(algospeak_df)} instances")
    if algospeak_summary is not None:
        print(f"  Algospeak summary: {len(algospeak_summary)} videos")
    
    # Generate all sensitivity charts
    print("\n--- Sensitivity Analysis RQ1 ---")
    if main_df is not None:
        chart1_risk_vs_ads_scatter(main_df, charts_dir)
        chart2_risk_by_ads_boxplot(main_df, charts_dir)
        chart3_risk_vs_year_scatter(main_df, charts_dir)
        chart4_avg_risk_by_ads_bar(main_df, charts_dir)
        chart5_risk_vs_views_scatter(main_df, charts_dir)
        chart6_risk_histogram(main_df, charts_dir)
        chart7_classification_pie(main_df, charts_dir)
    
    # Generate perception charts
    print("\n--- Perception Analysis RQ2 ---")
    chart8_perception_categories(perception_df, charts_dir)
    chart9_top_videos_perception(perception_df, charts_dir)
    
    # Generate algospeak charts
    print("\n--- Algospeak Analysis RQ3 ---")
    chart10_algospeak_transcript_vs_comments(algospeak_summary, charts_dir)
    chart11_top_algospeak_terms(algospeak_df, charts_dir)
    chart12_algospeak_by_category(algospeak_df, charts_dir)
    
    # Generate combined scatter chart
    print("\n--- Combined Insights ---")
    chart13_risk_vs_algospeak(main_df, algospeak_summary, charts_dir)
    
    print("\nSUCCESS: All visualizations generated")
    print(f"Charts saved to: {charts_dir}")
    print("Generated 13 charts: 7 sensitivity, 2 perception, 3 algospeak, 1 combined")
    print("ALL STEPS COMPLETE!")


# Entry point
if __name__ == "__main__":
    main()
