
# Step 7: Generate Visualizations

# Create charts and graphs from the analysis results.

# Charts generated:
#   Sensitivity Analysis (RQ1):
#     01. Scatter: Risk% vs Starting Ads
#     02. Box plot: Risk% by Ad Status
#     03. Scatter: Risk% vs Upload Year
#     04. Bar: Average Risk% by Ad Status
#     05. Scatter: Risk% vs View Count
#     06. Histogram: Risk% Distribution
#     07. Pie: Classification Distribution

#   Perception Analysis (RQ2):
#     08. Bar: Perception Categories
#     09. Bar: Top Videos by Perception Ratio
    
#   Algospeak Analysis (RQ3):
#     10. Grouped Bar: Algospeak in Transcripts vs Comments
#     11. Horizontal Bar: Top Algospeak Terms
#     12. Pie: Algospeak by Category
    
#   Combined Insights:
#     13. Scatter: Risk% vs Algospeak Count

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing library - {e}")
    print("Run: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Figure settings
FIGSIZE = (10, 6)
DPI = 150

def setup_chart_dir(base_dir: str) -> str:
    # Create charts directory if it doesn't exist.
    charts_dir = os.path.join(base_dir, DATA_OUTPUT_DIR, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir

def load_data(base_dir: str) -> dict:
    # Load all analysis data.
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    data = {}
    
    # Main analysis
    excel_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    if os.path.exists(excel_path):
        data['main'] = pd.read_excel(excel_path, sheet_name='Main Analysis')
    
    # Comments perception summary
    perception_path = os.path.join(output_dir, 'comments_perception_summary.csv')
    if os.path.exists(perception_path):
        data['perception'] = pd.read_csv(perception_path)
    
    # Algospeak findings
    algospeak_path = os.path.join(output_dir, 'algospeak_findings.csv')
    if os.path.exists(algospeak_path):
        data['algospeak'] = pd.read_csv(algospeak_path)
    
    # Algospeak summary
    algospeak_summary_path = os.path.join(output_dir, 'algospeak_findings_summary.csv')
    if os.path.exists(algospeak_summary_path):
        data['algospeak_summary'] = pd.read_csv(algospeak_summary_path)
    
    return data
    
def generate_charts(data: dict, chart_dir: str):    
    # Generate and save all charts.
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Example Chart 1: Scatter Plot of Risk% vs Starting Ads
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=data['sensitivity'], x='sensitive_term_ratio', y='starting_ads')
    plt.title('Risk% vs Starting Ads')
    plt.xlabel('Sensitive Term Ratio (%)')
    plt.ylabel('Starting Ads')
    plt.savefig(os.path.join(chart_dir, '01_risk_vs_starting_ads.png'))
    plt.close()
    
    # Sensitivity Analysis Charts (RQ1)

def chart1_risk_vs_ads_scatter(df: pd.DataFrame, charts_dir: str):
    # Chart 1: Scatter plot of Risk% vs Starting Ads.
    print("  01: Risk% vs Starting Ads (scatter)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    ad_col = None
    for col in ['starting_ads', 'manual_starting_ads']:
        if col in df.columns:
            ad_col = col
            break
    
    if ad_col is None:
        print("      SKIP: No ad status column")
        return
    
    plot_df = df[['sensitive_ratio', ad_col]].dropna()
    plot_df[ad_col] = plot_df[ad_col].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df[ad_col].isin(['yes', 'no'])]
    
    if plot_df.empty:
        print("      SKIP: No valid data")
        return
    
    colors = plot_df[ad_col].map({'yes': '#2ecc71', 'no': '#e74c3c'})
    
    ax.scatter(plot_df[ad_col].map({'yes': 1, 'no': 0}), 
               plot_df['sensitive_ratio'], 
               c=colors, alpha=0.7, s=100, edgecolors='white', linewidth=1)
    
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])
    ax.set_ylabel('Sensitive Ratio (%)', fontsize=12)
    ax.set_xlabel('Starting Ads', fontsize=12)
    ax.set_title('Risk % vs Starting Ad Status', fontsize=14, fontweight='bold')
    
    ax.axhline(y=2.0, color='orange', linestyle='--', alpha=0.7, label='T2 Threshold (2%)')
    ax.axhline(y=3.0, color='red', linestyle='--', alpha=0.7, label='T1 Threshold (3%)')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '01_risk_vs_ads_scatter.png'), dpi=DPI)
    plt.close()
    

def chart2_risk_by_ads_boxplot(df: pd.DataFrame, charts_dir: str):
    # Chart 2: Box plot of Risk% by Ad Status.
    print("  02: Risk% by Ad Status (box plot)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    ad_col = None
    for col in ['starting_ads', 'manual_starting_ads']:
        if col in df.columns:
            ad_col = col
            break
    
    if ad_col is None:
        print("      SKIP: No ad status column")
        return
    
    plot_df = df[['sensitive_ratio', ad_col]].dropna()
    plot_df[ad_col] = plot_df[ad_col].astype(str).str.strip().str.lower()
    plot_df = plot_df[plot_df[ad_col].isin(['yes', 'no'])]
    
    if plot_df.empty:
        print("      SKIP: No valid data")
        return
    
    sns.boxplot(data=plot_df, x=ad_col, y='sensitive_ratio', 
                hue=ad_col, palette={'yes': '#2ecc71', 'no': '#e74c3c'}, 
                ax=ax, legend=False)
    
    ax.set_xlabel('Starting Ads', fontsize=12)
    ax.set_ylabel('Sensitive Ratio (%)', fontsize=12)
    ax.set_title('Distribution of Risk % by Ad Status', fontsize=14, fontweight='bold')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No Ads', 'Has Ads'])
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '02_risk_by_ads_boxplot.png'), dpi=DPI)
    plt.close()
    


def chart3_risk_vs_year_scatter(df: pd.DataFrame, charts_dir: str):
    # Chart 3: Scatter plot of Risk% vs Upload Year.
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    if 'published_at' not in df.columns:
        print("      SKIP: No published_at column")
        return
    
    ax.set_xlabel('Upload Year', fontsize=12)
    ax.set_ylabel('Sensitive Ratio (%)', fontsize=12)
    ax.set_title('Risk % Over Time (by Upload Year)', fontsize=14, fontweight='bold')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '03_risk_vs_year_scatter.png'), dpi=DPI)
    plt.close()
    

def chart4_avg_risk_by_ads_bar(df: pd.DataFrame, charts_dir: str):
    # Chart 4: Bar chart of Average Risk% by Ad Status.
    print("  04: Average Risk% by Ad Status (bar)")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    ad_col = None
    for col in ['starting_ads', 'manual_starting_ads']:
        if col in df.columns:
            ad_col = col
            break
    
    if ad_col is None:
        print("      SKIP: No ad status column")
        return
   

def chart5_risk_vs_views_scatter(df: pd.DataFrame, charts_dir: str):
    # Chart 5: Scatter plot of Risk% vs View Count.
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
    ax.set_xlabel('View Count (log scale)', fontsize=12)
    ax.set_ylabel('Sensitive Ratio (%)', fontsize=12)
    ax.set_title('Risk % vs View Count', fontsize=14, fontweight='bold')
    
    

def chart6_risk_histogram(df: pd.DataFrame, charts_dir: str):
    # Chart 6: Histogram of Risk% Distribution.
    print("  06: Risk% Distribution (histogram)")
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    plot_df = df['sensitive_ratio'].dropna()
    
    if plot_df.empty:
        print("      SKIP: No valid data")
        return
    
    ax.hist(plot_df, bins=20, color='#3498db', edgecolor='white', alpha=0.8)
    
    ax.axvline(x=2.0, color='orange', linestyle='--', linewidth=2, label='T2 Threshold (2%)')
    ax.axvline(x=3.0, color='red', linestyle='--', linewidth=2, label='T1 Threshold (3%)')
    

def chart7_classification_pie(df: pd.DataFrame, charts_dir: str):
    # Chart 7: Pie chart of Classification Distribution.
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
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '07_classification_pie.png'), dpi=DPI)
    plt.close()
    
# Perception Analysis Charts (RQ2)

def chart8_perception_categories(perception_df: pd.DataFrame, charts_dir: str):
    # Chart 8: Bar chart of Perception Keyword Categories.
    print("  08: Perception Categories (bar)")
    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Find category columns (ending with _mentions)
    category_cols = [c for c in perception_df.columns if c.endswith('_mentions')]
    
    if not category_cols:
        print("      SKIP: No category columns found")
        return
    
    # Sum up all categories
    category_totals = {}
    for col in category_cols:
        category_name = col.replace('_mentions', '').replace('_', ' ').title()
        category_totals[category_name] = perception_df[col].sum()
    
    # Sort by value
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_cats]
    values = [c[1] for c in sorted_cats]
    
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(categories)))
    bars = ax.barh(categories, values, color=colors, edgecolor='white', linewidth=1)
    
    ax.set_xlabel('Number of Comments', fontsize=12)
    ax.set_ylabel('Perception Category', fontsize=12)
    ax.set_title('Perception Keywords by Category (RQ2)', fontsize=14, fontweight='bold')
    
    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{int(val)}', ha='left', va='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '08_perception_categories.png'), dpi=DPI)
    plt.close()

def chart9_top_videos_perception(perception_df: pd.DataFrame, charts_dir: str):
    # Chart 9: Top Videos by Perception Ratio.
    print("  09: Top Videos by Perception Ratio (bar)")

    if algospeak_summary is None or algospeak_summary.empty:
        print("      SKIP: No algospeak summary data")
        return
    
    if 'transcript_instances' not in algospeak_summary.columns:
        print("      SKIP: Missing required columns")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    

def chart10_algospeak_transcript_vs_comments(algospeak_summary: pd.DataFrame, charts_dir: str):
    # Chart 10: Algospeak in Transcripts vs Comments.
    print("  10: Algospeak Transcripts vs Comments (grouped bar)")
 

def chart11_top_algospeak_terms(algospeak_df: pd.DataFrame, charts_dir: str):
    # Chart 11: Top Algospeak Terms Used.
    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Count by term
    term_counts = algospeak_df.groupby('algospeak_term')['occurrences'].sum()
    top_terms = term_counts.nlargest(15)
    
    if top_terms.empty:
        print("      SKIP: No terms found")
        return
    
    colors = plt.cm.plasma(np.linspace(0.2, 0.8, len(top_terms)))
    bars = ax.barh(range(len(top_terms)), top_terms.values, color=colors)
    
    ax.set_yticks(range(len(top_terms)))
    ax.set_yticklabels(top_terms.index)
    ax.set_xlabel('Total Occurrences', fontsize=12)
    ax.set_title('Top 15 Algospeak Terms Used', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    
    # Add value labels with meaning
    meanings = algospeak_df.drop_duplicates('algospeak_term').set_index('algospeak_term')['original_meaning']
    for i, (term, val) in enumerate(top_terms.items()):
        meaning = meanings.get(term, '')[:20]
        ax.text(val + 0.5, i, f'{int(val)} ({meaning})', ha='left', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, '11_top_algospeak_terms.png'), dpi=DPI)
    plt.close()

def chart12_algospeak_by_category(algospeak_df: pd.DataFrame, charts_dir: str):
    # Chart 12: Algospeak by Category.
    print("  12: Algospeak by Category (pie)")
    if algospeak_df is None or algospeak_df.empty:
        print("      SKIP: No algospeak data")
        return
    
    if 'category' not in algospeak_df.columns:
        print("      SKIP: No category column")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Count by category
    category_counts = algospeak_df.groupby('category')['occurrences'].sum()
    category_counts = category_counts[category_counts > 0]
    
    if category_counts.empty:
        print("      SKIP: No categories found")
        return


# Combined Insight Charts

def chart13_risk_vs_algospeak(main_df: pd.DataFrame, algospeak_summary: pd.DataFrame, charts_dir: str):
    # Chart 13: Risk% vs Algospeak Count. 
    print("  13: Risk% vs Algospeak Count (scatter)")
    if main_df is None or algospeak_summary is None:
        print("      SKIP: Missing data")
        return
    
    fig, ax = plt.subplots(figsize=FIGSIZE)
    
    # Merge data
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
    
    
    # Merge data
    # Add trend line if enough points
    # Calculate correlation

def main():
    """Main function to generate visualizations."""
    chart_dir = setup_chart_dir(DATA_OUTPUT_DIR)
    data = load_data(DATA_OUTPUT_DIR)
    generate_charts(data, chart_dir)
    print(f"Charts saved in: {chart_dir}")
    # Setup paths
    # Load data
    # Generate charts
if __name__ == "__main__":
    main()

