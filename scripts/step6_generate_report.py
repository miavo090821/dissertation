# Step 6: Generate Final Report

# Compile all analysis results into a comprehensive Excel report.
# Combines metadata, sensitivity analysis, comments analysis, and algospeak findings.
import sys
import os
import csv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_csv_if_exists(path: str) -> pd.DataFrame:
# Load CSV file if it exists, otherwise return empty DataFrame.
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()       
try:
    from config import DATA_OUTPUT_DIR, FINAL_REPORT_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1) 
    
def load_input_csv(base_dir: str) -> pd.DataFrame:
def extract_video_id_from_url(url: str) -> str:
def calculate_upload_age(published_at: str) -> tuple:
  
    
import pandas as pd
def generate_final_report():
    # Load all analysis results
    metadata_df = load_csv_if_exists(os.path.join(DATA_OUTPUT_DIR, 'metadata_analysis.csv'))
    sensitivity_df = load_csv_if_exists(os.path.join(DATA_OUTPUT_DIR, 'sensitivity_analysis.csv'))
    comments_df = load_csv_if_exists(os.path.join(DATA_OUTPUT_DIR, 'comments_analysis.csv'))
    algospeak_df = load_csv_if_exists(os.path.join(DATA_OUTPUT_DIR, 'algospeak_findings.csv'))
    
    # Merge dataframes on 'video_id'
    report_df = metadata_df
    if not sensitivity_df.empty:
        report_df = report_df.merge(sensitivity_df, on='video_id', how='left')
    if not comments_df.empty:
        report_df = report_df.merge(comments_df, on='video_id', how='left')
    if not algospeak_df.empty:
        report_df = report_df.merge(algospeak_df, on='video_id', how='left')
    
    # Save final report to Excel
    report_path = os.path.join(DATA_OUTPUT_DIR, FINAL_REPORT_FILE)
    report_df.to_excel(report_path, index=False)
    print(f"Final report generated: {report_path}") 
if __name__ == "__main__":
    generate_final_report()
