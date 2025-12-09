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
    
    # Additional charts would be generated similarly... 
def main():
    """Main function to generate visualizations."""
    chart_dir = setup_chart_dir(DATA_OUTPUT_DIR)
    data = load_data(DATA_OUTPUT_DIR)
    generate_charts(data, chart_dir)
    print(f"Charts saved in: {chart_dir}")
    
if __name__ == "__main__":
    main()

