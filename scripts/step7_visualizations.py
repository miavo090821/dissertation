# Step 7: Generate Visualizations
# Orchestrates chart generation across RQ1, RQ2, RQ3 and combined insights.
# Chart functions are in scripts/utils/chart_generators.py.
# Saves all charts to data/output/charts/ as PNG files.

import sys
import os

# Add parent directory so config and utils can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_OUTPUT_DIR, FINAL_REPORT_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError as e:
    print(f"ERROR: Missing library - {e}")
    print("Run: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

# Import all chart functions from the generators module
from scripts.utils.chart_generators import (
    chart1_risk_vs_ads_scatter,
    chart2_risk_by_ads_boxplot,
    chart3_risk_vs_year_scatter,
    chart4_avg_risk_by_ads_bar,
    chart5_risk_vs_views_scatter,
    chart6_risk_histogram,
    chart7_classification_pie,
    chart8_perception_categories,
    chart9_top_videos_perception,
    chart10_algospeak_transcript_vs_comments,
    chart11_top_algospeak_terms,
    chart12_algospeak_by_category,
    chart13_risk_vs_algospeak,
    chart14_sensitivity_by_category,
    chart15_category_correlation_heatmap,
)

# Set global chart style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def setup_chart_dir(base_dir: str) -> str:
    """Create chart directory if missing and return its path."""
    charts_dir = os.path.join(base_dir, DATA_OUTPUT_DIR, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir


def load_data(base_dir: str) -> dict:
    """Load all datasets required for chart generation."""
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

    # Load category cross-analysis
    category_path = os.path.join(output_dir, 'category_analysis.csv')
    if os.path.exists(category_path):
        data['category'] = pd.read_csv(category_path)

    # Load sensitivity scores (has per-category columns)
    sensitivity_path = os.path.join(output_dir, 'sensitivity_scores.csv')
    if os.path.exists(sensitivity_path):
        data['sensitivity'] = pd.read_csv(sensitivity_path)

    return data


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
    category_df = data.get('category')
    sensitivity_df = data.get('sensitivity')

    # Print loaded dataset sizes
    if main_df is not None:
        print(f"  Main analysis: {len(main_df)} videos")
    if perception_df is not None:
        print(f"  Perception data: {len(perception_df)} videos")
    if algospeak_df is not None:
        print(f"  Algospeak findings: {len(algospeak_df)} instances")
    if algospeak_summary is not None:
        print(f"  Algospeak summary: {len(algospeak_summary)} videos")

    # RQ1: Sensitivity Analysis (7 charts)
    print("\n--- Sensitivity Analysis RQ1 ---")
    if main_df is not None:
        chart1_risk_vs_ads_scatter(main_df, charts_dir)
        chart2_risk_by_ads_boxplot(main_df, charts_dir)
        chart3_risk_vs_year_scatter(main_df, charts_dir)
        chart4_avg_risk_by_ads_bar(main_df, charts_dir)
        chart5_risk_vs_views_scatter(main_df, charts_dir)
        chart6_risk_histogram(main_df, charts_dir)
        chart7_classification_pie(main_df, charts_dir)

    # RQ2: Perception Analysis (2 charts)
    print("\n--- Perception Analysis RQ2 ---")
    chart8_perception_categories(perception_df, charts_dir)
    chart9_top_videos_perception(perception_df, charts_dir)

    # RQ3: Algospeak Analysis (3 charts)
    print("\n--- Algospeak Analysis RQ3 ---")
    chart10_algospeak_transcript_vs_comments(algospeak_summary, charts_dir)
    chart11_top_algospeak_terms(algospeak_df, charts_dir)
    chart12_algospeak_by_category(algospeak_df, charts_dir)

    # Combined Insights (1 chart)
    print("\n--- Combined Insights ---")
    chart13_risk_vs_algospeak(main_df, algospeak_summary, charts_dir)

    # Category Analysis (2 charts)
    print("\n--- Category Analysis ---")
    chart14_sensitivity_by_category(sensitivity_df, charts_dir)
    chart15_category_correlation_heatmap(category_df, charts_dir)

    print("\nSUCCESS: All visualizations generated")
    print(f"Charts saved to: {charts_dir}")
    print("Generated 15 charts: 7 sensitivity, 2 perception, 3 algospeak, 1 combined, 2 category")
    print("ALL STEPS COMPLETE!")


if __name__ == "__main__":
    main()
