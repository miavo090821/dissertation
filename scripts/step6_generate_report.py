# Step 6 Generate Final Report
# This script compiles all analysis outputs into one Excel report
# It combines sensitivity scores comments analysis algospeak findings and manual ad status
# Usage
# python scripts/step6_generate_report.py

import sys
import os
import csv
import json
from datetime import datetime

# Add parent directory to import path so config and utils can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import project wide configuration and file names
    from config import (
        DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR,
        SENSITIVITY_SCORES_FILE, COMMENTS_ANALYSIS_FILE, 
        ALGOSPEAK_FINDINGS_FILE, FINAL_REPORT_FILE
    )
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

try:
    # Pandas is required for DataFrame operations and Excel export
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas openpyxl")
    sys.exit(1)

# Import duration helper functions for formatting video length
from scripts.utils.youtube_api import parse_duration, format_duration


# Load a csv file if it exists otherwise return an empty DataFrame
def load_csv_if_exists(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


# Load the input video list including manual ad status annotations
def load_input_csv(base_dir: str) -> pd.DataFrame:
    input_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')
    if os.path.exists(input_path):
        return pd.read_csv(input_path)
    return pd.DataFrame()


# Extract a YouTube video id from a full url or plain id string
def extract_video_id_from_url(url: str) -> str:
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


# Compute how long ago a video was uploaded expressed in human friendly units
def calculate_upload_age(published_at: str) -> tuple:
    if not published_at:
        return None, ""
    
    try:
        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
        delta = now - pub_date
        
        days = delta.days
        
        if days < 7:
            return days, "days"
        elif days < 30:
            return round(days / 7, 1), "weeks"
        elif days < 365:
            return round(days / 30, 1), "months"
        else:
            return round(days / 365, 1), "years"
    except:
        return None, ""


def main():
    # Set up base and output paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    
    # Build full paths for all input and output csv files
    sensitivity_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    comments_summary_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE.replace('.csv', '_summary.csv'))
    algospeak_summary_path = os.path.join(output_dir, ALGOSPEAK_FINDINGS_FILE.replace('.csv', '_summary.csv'))
    output_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    
    # High level progress header
    print("=" * 70)
    print("STEP 6: GENERATE FINAL REPORT")
    print("=" * 70)
    
    # Load all intermediate analysis outputs
    print("\nLoading data sources...")
    
    sensitivity_df = load_csv_if_exists(sensitivity_path)
    print(f"  Sensitivity scores: {len(sensitivity_df)} videos")
    
    comments_df = load_csv_if_exists(comments_summary_path)
    print(f"  Comments analysis: {len(comments_df)} videos")
    
    algospeak_df = load_csv_if_exists(algospeak_summary_path)
    print(f"  Algospeak findings: {len(algospeak_df)} videos")
    
    input_df = load_input_csv(base_dir)
    print(f"  Input CSV: {len(input_df)} videos")
    
    # Sensitivity analysis is the core table so it must exist
    if sensitivity_df.empty:
        print("\nERROR: No sensitivity analysis data found.")
        print("Please run step3_sensitivity_analysis.py first")
        sys.exit(1)
    
    # Start master DataFrame with sensitivity results
    master_df = sensitivity_df.copy()
    
    # Merge in comments perception summary using dynamic columns
    if not comments_df.empty:
        # Keep video id and other columns but avoid duplicate title column
        comments_cols = [c for c in comments_df.columns if c != 'title']
        if 'video_id' in comments_cols:
            master_df = master_df.merge(
                comments_df[comments_cols],
                on='video_id',
                how='left'
            )
    
    # Merge algospeak aggregate metrics if they are present
    if not algospeak_df.empty:
        algospeak_cols = ['video_id', 'total_algospeak_instances', 'unique_terms_found']
        available_cols = [c for c in algospeak_cols if c in algospeak_df.columns]
        if available_cols:
            master_df = master_df.merge(
                algospeak_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # Merge ad status from input csv if not already present from sensitivity scores
    if 'ad_status' not in master_df.columns and not input_df.empty and 'url' in input_df.columns:
        input_df['video_id'] = input_df['url'].apply(extract_video_id_from_url)
        input_cols = ['video_id', 'ad_status']
        available_cols = [c for c in input_cols if c in input_df.columns]
        # Only merge if there is at least one metric besides id
        if len(available_cols) > 1:
            master_df = master_df.merge(
                input_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # Compute additional derived fields for the report
    print("\nCalculating derived fields...")
    
    # Upload age in days weeks months or years
    if 'published_at' in master_df.columns:
        age_data = master_df['published_at'].apply(calculate_upload_age)
        master_df['upload_age'] = [a[0] for a in age_data]
        master_df['upload_age_type'] = [a[1] for a in age_data]
    
    # Duration converted from iso period to nice text representation
    if 'duration' in master_df.columns:
        master_df['duration_formatted'] = master_df['duration'].apply(
            lambda x: format_duration(parse_duration(x)) if pd.notna(x) else ''
        )
    
    # Replace missing values with empty strings for a clean Excel view
    master_df = master_df.fillna('')
    
    # Choose column order so the most useful fields appear first
    priority_cols = [
        'video_id', 'title', 'channel_name', 'published_at',
        'duration_formatted', 'upload_age', 'upload_age_type',
        'view_count', 'like_count', 'comment_count',
        'total_words', 'sensitive_count', 'sensitive_ratio', 'classification',
        'ad_status'
    ]
    
    # Build final column order by adding remaining columns after priority group
    ordered_cols = [c for c in priority_cols if c in master_df.columns]
    remaining_cols = [c for c in master_df.columns if c not in ordered_cols]
    master_df = master_df[ordered_cols + remaining_cols]
    
    # Create Excel workbook with multiple sheets for different views
    print(f"\nWriting Excel report: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main sheet with unified view over all metrics
        master_df.to_excel(writer, sheet_name='Main Analysis', index=False)
        
        # Raw sensitivity analysis scores
        if not sensitivity_df.empty:
            sensitivity_df.to_excel(writer, sheet_name='Sensitivity Details', index=False)
        
        # Comments perception summary per video
        if not comments_df.empty:
            comments_df.to_excel(writer, sheet_name='Comments Analysis', index=False)
        
        # Algospeak metrics per video
        if not algospeak_df.empty:
            algospeak_df.to_excel(writer, sheet_name='Algospeak Findings', index=False)
        
        # Build summary statistics sheet for quick overview
        summary_metrics = [
            ('Total Videos', len(master_df)),
            ('Average Sensitive Ratio %', round(master_df['sensitive_ratio'].mean(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Min Sensitive Ratio %', round(master_df['sensitive_ratio'].min(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Max Sensitive Ratio %', round(master_df['sensitive_ratio'].max(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Likely Monetised', len(master_df[master_df['classification'] == 'Likely Monetised']) if 'classification' in master_df.columns else 'N/A'),
            ('Uncertain', len(master_df[master_df['classification'] == 'Uncertain']) if 'classification' in master_df.columns else 'N/A'),
            ('Likely Demonetised', len(master_df[master_df['classification'] == 'Likely Demonetised']) if 'classification' in master_df.columns else 'N/A'),
        ]
        
        # Add aggregate algospeak information if present
        if 'total_algospeak_instances' in master_df.columns:
            algospeak_videos = len(master_df[master_df['total_algospeak_instances'] > 0])
            summary_metrics.append(('Videos with Algospeak', algospeak_videos))
        
        # Add perception comment count if present
        if 'perception_comments' in master_df.columns:
            perception_sum = pd.to_numeric(master_df['perception_comments'], errors='coerce').sum()
            summary_metrics.append(('Total Perception Comments', int(perception_sum) if not pd.isna(perception_sum) else 0))
        
        summary_df = pd.DataFrame(summary_metrics, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
    
    # Final success messages with helpful next step
    print("\nSUCCESS: Excel report generated")
    print(f"Report saved to: {output_path}")
    print("Sheets: Main Analysis, Sensitivity Details, Comments Analysis, Algospeak Findings, Summary Statistics")
    print("Next: Run step7_visualizations.py")


if __name__ == "__main__":
    main()
