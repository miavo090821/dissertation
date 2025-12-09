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

def load_input_csv(base_dir: str) -> pd.DataFrame:
    """Load the input CSV containing video URLs and IDs."""
    input_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')
    if os.path.exists(input_path):
        return pd.read_csv(input_path)
    return pd.DataFrame()
    
def extract_video_id_from_url(url: str) -> str:
    # Extract video ID from URL for matching.
    import re
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]
    for pattern in patterns:
        match = re.search(pattern, str(url))
        if match:
            return match.group(1)
    return ""

def calculate_upload_age(published_at: str) -> tuple:
    if not published_at:
        return None, ""
    
    
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

def main():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    
    sensitivity_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    comments_summary_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE.replace('.csv', '_summary.csv'))
    algospeak_summary_path = os.path.join(output_dir, ALGOSPEAK_FINDINGS_FILE.replace('.csv', '_summary.csv'))
    output_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    
    print("=" * 70)
    print("STEP 6: GENERATE FINAL REPORT")
    print("=" * 70)   
    
    # Duration in formatted string
    if 'duration' in master_df.columns:
        master_df['duration_formatted'] = master_df['duration'].apply(
            lambda x: format_duration(parse_duration(x)) if pd.notna(x) else ''
        )
        
    # Create Excel file with multiple sheets
    print(f"\nWriting Excel report: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main analysis sheet
        master_df.to_excel(writer, sheet_name='Main Analysis', index=False)
        
    print("\nSUCCESS: Excel report generated")
    print(f"Report saved to: {output_path}")
if __name__ == "__main__":
    generate_final_report()
