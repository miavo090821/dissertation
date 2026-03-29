# step 7: generate visualizations
#
# 1. this script creates all the charts used in the dissertation
# 2. it loads the final datasets and passes them into pre-built chart functions
# 3. rq1 includes 7 sensitivity charts, rq2 includes 2 perception charts, and rq3 includes 3 algospeak charts
# 4. it also creates 1 combined insights chart and 2 category analysis charts
# 5. all charts are saved as png files in data/output/charts/

import sys  # used to stop the script early if something important is missing
import os   # used for file paths, folder creation, and checking whether files exist

# add the parent project directory to the python path
# this lets the script import config.py and utility modules from the main project folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import shared config values:
    # - DATA_OUTPUT_DIR tells us where outputs are stored
    # - FINAL_REPORT_FILE is the excel file created in step 6
    from config import DATA_OUTPUT_DIR, FINAL_REPORT_FILE
except ImportError:
    # stop the script if config.py cannot be found
    print("ERROR: config.py not found!")
    sys.exit(1)

try:
    import pandas as pd              # used to load csv and excel files into dataframes
    import matplotlib.pyplot as plt  # used for chart styling and figure handling
    import seaborn as sns            # used to apply cleaner chart themes and colour palettes
except ImportError as e:
    # stop the script if one of the required chart libraries is missing
    print(f"ERROR: Missing library - {e}")
    print("Run: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

# import all chart-making functions from the utility module
# each function creates one chart and saves it to the charts folder
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

# set a global visual style for all plots
# this helps all dissertation charts look consistent
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def setup_chart_dir(base_dir: str) -> str:
    """Create the charts folder if it does not already exist, then return the path."""
    charts_dir = os.path.join(base_dir, DATA_OUTPUT_DIR, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir


def load_data(base_dir: str) -> dict:
    """Load all datasets needed for chart generation and return them in a dictionary."""
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    data = {}

    # load the main combined analysis sheet from the final excel report
    # this is the main dataset used by many of the rq1 and combined charts
    excel_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    if os.path.exists(excel_path):
        data['main'] = pd.read_excel(excel_path, sheet_name='Main Analysis')

    # load the comments perception summary
    # this is used for rq2 charts about viewer/creator perceptions
    perception_path = os.path.join(output_dir, 'comments_perception_summary.csv')
    if os.path.exists(perception_path):
        data['perception'] = pd.read_csv(perception_path)

    # load detailed algospeak findings at instance level
    # this means one row may represent one algospeak match rather than one whole video
    algospeak_path = os.path.join(output_dir, 'algospeak_findings.csv')
    if os.path.exists(algospeak_path):
        data['algospeak'] = pd.read_csv(algospeak_path)

    # load algospeak summary at video level
    # this is more useful when comparing total algospeak usage across videos
    algospeak_summary_path = os.path.join(output_dir, 'algospeak_findings_summary.csv')
    if os.path.exists(algospeak_summary_path):
        data['algospeak_summary'] = pd.read_csv(algospeak_summary_path)

    # load category cross-analysis data
    # this helps compare sensitive word categories with algospeak categories
    category_path = os.path.join(output_dir, 'category_analysis.csv')
    if os.path.exists(category_path):
        data['category'] = pd.read_csv(category_path)

    # load sensitivity scores
    # this file usually includes per-category sensitivity counts as well
    sensitivity_path = os.path.join(output_dir, 'sensitivity_scores.csv')
    if os.path.exists(sensitivity_path):
        data['sensitivity'] = pd.read_csv(sensitivity_path)

    return data


def main():
    # find the main project folder and prepare the charts output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    charts_dir = setup_chart_dir(base_dir)

    # print a clear step header so it is obvious what part of the pipeline is running
    print("=" * 70)
    print("STEP 7: GENERATE VISUALIZATIONS")
    print("=" * 70)

    # load all available datasets needed for chart creation
    print("\nLoading data...")
    data = load_data(base_dir)

    # pull each dataset out of the dictionary
    # .get() is used so missing files return None instead of crashing
    main_df = data.get('main')
    perception_df = data.get('perception')
    algospeak_df = data.get('algospeak')
    algospeak_summary = data.get('algospeak_summary')
    category_df = data.get('category')
    sensitivity_df = data.get('sensitivity')

    # print how many rows were loaded for each dataset
    # this makes it easier to check whether the right files were found
    if main_df is not None:
        print(f"  Main analysis: {len(main_df)} videos")
    if perception_df is not None:
        print(f"  Perception data: {len(perception_df)} videos")
    if algospeak_df is not None:
        print(f"  Algospeak findings: {len(algospeak_df)} instances")
    if algospeak_summary is not None:
        print(f"  Algospeak summary: {len(algospeak_summary)} videos")

    # RQ1: sensitivity analysis
    # these charts focus on sensitive language, risk scores, and monetisation status
    print("\n--- Sensitivity Analysis RQ1 ---")
    if main_df is not None:
        chart1_risk_vs_ads_scatter(main_df, charts_dir)
        chart2_risk_by_ads_boxplot(main_df, charts_dir)
        chart3_risk_vs_year_scatter(main_df, charts_dir)
        chart4_avg_risk_by_ads_bar(main_df, charts_dir)
        chart5_risk_vs_views_scatter(main_df, charts_dir)
        chart6_risk_histogram(main_df, charts_dir)
        chart7_classification_pie(main_df, charts_dir)

    # RQ2: perception analysis
    # these charts focus on how demonetisation is discussed or perceived in comments
    print("\n--- Perception Analysis RQ2 ---")
    chart8_perception_categories(perception_df, charts_dir)
    chart9_top_videos_perception(perception_df, charts_dir)

    # RQ3: algospeak analysis
    # these charts focus on coded language patterns in transcripts and comments
    print("\n--- Algospeak Analysis RQ3 ---")
    chart10_algospeak_transcript_vs_comments(algospeak_summary, charts_dir)
    chart11_top_algospeak_terms(algospeak_df, charts_dir)
    chart12_algospeak_by_category(algospeak_df, charts_dir)

    # combined insights
    # this chart connects sensitivity and algospeak together in one view
    print("\n--- Combined Insights ---")
    chart13_risk_vs_algospeak(main_df, algospeak_summary, charts_dir)

    # category analysis
    # these charts look at category-level patterns rather than only overall totals
    print("\n--- Category Analysis ---")
    chart14_sensitivity_by_category(sensitivity_df, charts_dir)
    chart15_category_correlation_heatmap(category_df, charts_dir)

    # final success message so the user knows the pipeline has finished
    print("\nSUCCESS: All visualizations generated")
    print(f"Charts saved to: {charts_dir}")
    print("Generated 15 charts: 7 sensitivity, 2 perception, 3 algospeak, 1 combined, 2 category")
    print("ALL STEPS COMPLETE!")


if __name__ == "__main__":
    main()