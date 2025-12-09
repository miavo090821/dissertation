"""
Step 7: Generate Visualizations

Create charts and graphs from the analysis results.

Charts generated:
  Sensitivity Analysis (RQ1):
    01. Scatter: Risk% vs Starting Ads
    02. Box plot: Risk% by Ad Status
    03. Scatter: Risk% vs Upload Year
    04. Bar: Average Risk% by Ad Status
    05. Scatter: Risk% vs View Count
    06. Histogram: Risk% Distribution
    07. Pie: Classification Distribution

  Perception Analysis (RQ2):
    08. Bar: Perception Categories
    09. Bar: Top Videos by Perception Ratio
    
  Algospeak Analysis (RQ3):
    10. Grouped Bar: Algospeak in Transcripts vs Comments
    11. Horizontal Bar: Top Algospeak Terms
    12. Pie: Algospeak by Category
    
  Combined Insights:
    13. Scatter: Risk% vs Algospeak Count

"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_OUTPUT_DIR, FINAL_REPORT_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

def setup_chart_dir(base_dir: str) -> str:
    """Set up directory for saving charts."""
    chart_dir = os.path.join(base_dir, 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    return chart_dir
def load_data(base_dir: str) -> dict:
    """Load all necessary CSV data for visualizations."""
    import pandas as pd

    data = {}
    data['sensitivity'] = pd.read_csv(os.path.join(base_dir, 'sensitivity_analysis.csv'))
    data['perception'] = pd.read_csv(os.path.join(base_dir, 'perception_analysis.csv'))
    data['algospeak'] = pd.read_csv(os.path.join(base_dir, 'algospeak_findings.csv'))
    data['final_report'] = pd.read_excel(os.path.join(base_dir, FINAL_REPORT_FILE))
    
    return data 
def generate_charts(data: dict, chart_dir: str):    
    """Generate and save all charts."""
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
    sns.scatterplot(data=df, x='sensitive_term_ratio', y='starting_ads', ax=ax)
    ax.set_title('Risk% vs Starting Ads')
    ax.set_xlabel('Sensitive Term Ratio (%)')
    ax.set_ylabel('Starting Ads')
    plt.savefig(os.path.join(charts_dir, '01_risk_vs_starting_ads.png'))
    plt.close() 
    

def chart2_risk_by_ads_boxplot(df: pd.DataFrame, charts_dir: str):
    # Chart 2: Box plot of Risk% by Ad Status.
    print("  02: Risk% by Ad Status (box plot)")
    fig, ax = plt.subplots(figsize=FIGSIZE)
    sns.boxplot(data=df, x='ad_status', y='sensitive_term_ratio', ax=ax)
    ax.set_title('Risk% by Ad Status')
    ax.set_xlabel('Ad Status')
    ax.set_ylabel('Sensitive Term Ratio (%)')
    plt.savefig(os.path.join(charts_dir, '02_risk_by_ad_status.png'))       
    plt.close() 
    

def chart3_risk_vs_year_scatter(df: pd.DataFrame, charts_dir: str):
    """Chart 3: Scatter plot of Risk% vs Upload Year."""
    print("  03: Risk% vs Upload Year (scatter)")


def chart4_avg_risk_by_ads_bar(df: pd.DataFrame, charts_dir: str):
    """Chart 4: Bar chart of Average Risk% by Ad Status."""
    print("  04: Average Risk% by Ad Status (bar)")
   

def chart5_risk_vs_views_scatter(df: pd.DataFrame, charts_dir: str):
    """Chart 5: Scatter plot of Risk% vs View Count."""
    print("  05: Risk% vs View Count (scatter)")
    

def chart6_risk_histogram(df: pd.DataFrame, charts_dir: str):
    """Chart 6: Histogram of Risk% Distribution."""
    print("  06: Risk% Distribution (histogram)")


def chart7_classification_pie(df: pd.DataFrame, charts_dir: str):
    """Chart 7: Pie chart of Classification Distribution."""
    print("  07: Classification Distribution (pie)")


# Perception Analysis Charts (RQ2)

def chart8_perception_categories(perception_df: pd.DataFrame, charts_dir: str):
    """Chart 8: Bar chart of Perception Keyword Categories."""
    print("  08: Perception Categories (bar)")
    
    if perception_df is None or perception_df.empty:
        print("      SKIP: No perception data")
        return


def chart9_top_videos_perception(perception_df: pd.DataFrame, charts_dir: str):
    """Chart 9: Top Videos by Perception Ratio."""
    print("  09: Top Videos by Perception Ratio (bar)")


def chart10_algospeak_transcript_vs_comments(algospeak_summary: pd.DataFrame, charts_dir: str):
    """Chart 10: Algospeak in Transcripts vs Comments."""
    print("  10: Algospeak Transcripts vs Comments (grouped bar)")
 

def chart11_top_algospeak_terms(algospeak_df: pd.DataFrame, charts_dir: str):
    """Chart 11: Top Algospeak Terms Used."""
    print("  11: Top Algospeak Terms (horizontal bar)")


def chart12_algospeak_by_category(algospeak_df: pd.DataFrame, charts_dir: str):
    """Chart 12: Algospeak by Category."""
    print("  12: Algospeak by Category (pie)")


# Combined Insight Charts

def chart13_risk_vs_algospeak(main_df: pd.DataFrame, algospeak_summary: pd.DataFrame, charts_dir: str):
    """Chart 13: Risk% vs Algospeak Count."""
    print("  13: Risk% vs Algospeak Count (scatter)")
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

