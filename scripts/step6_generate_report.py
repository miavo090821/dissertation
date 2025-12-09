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
    
    
    # Load data sources
    print("\nLoading data sources...")
    
    sensitivity_df = load_csv_if_exists(sensitivity_path)
    print(f"  Sensitivity scores: {len(sensitivity_df)} videos")
    
    comments_df = load_csv_if_exists(comments_summary_path)
    print(f"  Comments analysis: {len(comments_df)} videos")
    
    algospeak_df = load_csv_if_exists(algospeak_summary_path)
    print(f"  Algospeak findings: {len(algospeak_df)} videos")
    
    input_df = load_input_csv(base_dir)
    print(f"  Input CSV: {len(input_df)} videos")
    
    if sensitivity_df.empty:
        print("\nERROR: No sensitivity analysis data found.")
        print("Please run step3_sensitivity_analysis.py first")
        sys.exit(1)
    
    # Create master DataFrame starting from sensitivity analysis
    master_df = sensitivity_df.copy()
    
     # Merge with algospeaks analysis
    if not algospeak_df.empty:
        algospeak_cols = ['video_id', 'total_algospeak_instances', 'unique_terms_found']
        available_cols = [c for c in algospeak_cols if c in algospeak_df.columns]
        if available_cols:
            master_df = master_df.merge(
                algospeak_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # Merge with input CSV for manual ad status
    if not input_df.empty and 'url' in input_df.columns:
        input_df['video_id'] = input_df['url'].apply(extract_video_id_from_url)
        input_cols = ['video_id', 'starting_ads', 'mid_roll_ads', 'ad_breaks_detected']
        available_cols = [c for c in input_cols if c in input_df.columns]
        if len(available_cols) > 1:  # At least video_id + one other column
            master_df = master_df.merge(
                input_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # Duration in formatted string
    if 'duration' in master_df.columns:
        master_df['duration_formatted'] = master_df['duration'].apply(
            lambda x: format_duration(parse_duration(x)) if pd.notna(x) else ''
        )
    
    # Fill NaN values
    master_df = master_df.fillna('')
        
    # Get columns in preferred order, then add remaining
    ordered_cols = [c for c in priority_cols if c in master_df.columns]
    remaining_cols = [c for c in master_df.columns if c not in ordered_cols]
    master_df = master_df[ordered_cols + remaining_cols]
   
        
    # Create Excel file with multiple sheets
    print(f"\nWriting Excel report: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main analysis sheet
        master_df.to_excel(writer, sheet_name='Main Analysis', index=False)
        
        # Sensitivity details
        if not sensitivity_df.empty:
            sensitivity_df.to_excel(writer, sheet_name='Sensitivity Details', index=False)
        
        # Comments analysis
        if not comments_df.empty:
            comments_df.to_excel(writer, sheet_name='Comments Analysis', index=False)
        
        # Algospeak findings
        if not algospeak_df.empty:
            algospeak_df.to_excel(writer, sheet_name='Algospeak Findings', index=False)
        
        # Summary statistics
        summary_metrics = [
            ('Total Videos', len(master_df)),
            ('Average Sensitive Ratio %', round(master_df['sensitive_ratio'].mean(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Min Sensitive Ratio %', round(master_df['sensitive_ratio'].min(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Max Sensitive Ratio %', round(master_df['sensitive_ratio'].max(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Likely Monetised', len(master_df[master_df['classification'] == 'Likely Monetised']) if 'classification' in master_df.columns else 'N/A'),
            ('Uncertain', len(master_df[master_df['classification'] == 'Uncertain']) if 'classification' in master_df.columns else 'N/A'),
            ('Likely Demonetised', len(master_df[master_df['classification'] == 'Likely Demonetised']) if 'classification' in master_df.columns else 'N/A'),
        ]
        
        # Add algospeak stats if available
        if 'total_algospeak_instances' in master_df.columns:
            algospeak_videos = len(master_df[master_df['total_algospeak_instances'] > 0])
            summary_metrics.append(('Videos with Algospeak', algospeak_videos))
        
        # Add perception stats if available
        if 'perception_comments' in master_df.columns:
            perception_sum = pd.to_numeric(master_df['perception_comments'], errors='coerce').sum()
            summary_metrics.append(('Total Perception Comments', int(perception_sum) if not pd.isna(perception_sum) else 0))
        
        summary_df = pd.DataFrame(summary_metrics, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
    
    print("\nSUCCESS: Excel report generated")
    print(f"Report saved to: {output_path}")
    print("Sheets: Main Analysis, Sensitivity Details, Comments Analysis, Algospeak Findings, Summary Statistics")
    print("Next: Run step7_visualizations.py")
    
if __name__ == "__main__":
    generate_final_report()
