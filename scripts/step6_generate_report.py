# step 6: generate final report
#
# 1. this script brings together the outputs from steps 3 to 5 into one final excel report
# 2. it combines sensitivity scores, comments perception results, algospeak findings, and ad status
# 3. it also creates extra fields like upload age and a cleaner video duration format
# 4. the final output is a multi-sheet excel workbook, which is easier to use for analysis and dissertation write-up
# 5. run it with: python scripts/step6_generate_report.py

import sys                  
# used to exit the script early if something important is missing

import os                   
# used for file paths and checking whether files exist
import csv                  
# included for csv-related work, although pandas handles most csv loading here

import json                 
# included in case json data handling is needed in the report pipeline
from datetime import datetime   
# used to work out how old a video is based on its upload date


# add the parent directory to the python path
# this lets the script import config.py and utility modules from the project folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import project-wide folder paths and file names from config.py
    # this keeps file locations centralised instead of hardcoding them in the script
    from config import (
        DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR,
        SENSITIVITY_SCORES_FILE, COMMENTS_ANALYSIS_FILE, 
        ALGOSPEAK_FINDINGS_FILE, FINAL_REPORT_FILE
    )
except ImportError:
    # stop the script if config.py cannot be found
    print("ERROR: config.py not found!")
    sys.exit(1)

try:
    # pandas is the main library used here for:
    # - loading csv files into dataframes
    # - merging tables together
    # - creating the final excel workbook
    import pandas as pd
except ImportError:
    # stop the script if pandas is missing, because the report depends on it
    print("ERROR: pandas not installed. Run: pip install pandas openpyxl")
    sys.exit(1)

# import helper functions for turning youtube duration strings
# into a more readable format such as minutes and seconds
from scripts.utils.youtube_api import parse_duration, format_duration


# load a csv file only if it exists
# if the file is missing, return an empty dataframe instead of crashing
def load_csv_if_exists(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


# load the original input csv that contains the list of videos
# this is also where manual ad status annotations may be stored
def load_input_csv(base_dir: str) -> pd.DataFrame:
    input_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')
    if os.path.exists(input_path):
        return pd.read_csv(input_path)
    return pd.DataFrame()


# extract the youtube video id from either:
# - a full youtube url
# - or a plain 11-character video id
# this helps create a consistent key for merging different datasets
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


# work out how old the video is based on its published date
# returns both:
# - the number value
# - and the unit type (days, weeks, months, years)
# this is more readable than just showing the raw upload timestamp
def calculate_upload_age(published_at: str) -> tuple:
    if not published_at:
        return None, ""
    
    try:
        # convert the youtube timestamp into a python datetime object
        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

        # use the same timezone as the published date if it exists
        now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()

        # find the difference between now and the upload date
        delta = now - pub_date
        days = delta.days
        
        # convert raw days into a more human-friendly unit
        if days < 7:
            return days, "days"
        elif days < 30:
            return round(days / 7, 1), "weeks"
        elif days < 365:
            return round(days / 30, 1), "months"
        else:
            return round(days / 365, 1), "years"
    except:
        # if anything goes wrong with the date format, return blanks
        return None, ""


def main():
    # build the main project paths
    # base_dir = project root
    # output_dir = where analysis csv files are stored
    # raw_dir = raw data folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    
    # build the full file paths for the datasets we want to combine
    sensitivity_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    comments_summary_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE.replace('.csv', '_summary.csv'))
    algospeak_summary_path = os.path.join(output_dir, ALGOSPEAK_FINDINGS_FILE.replace('.csv', '_summary.csv'))
    output_path = os.path.join(output_dir, FINAL_REPORT_FILE)
    
    # print a clear header so it is obvious which step is running
    print("=" * 70)
    print("STEP 6: GENERATE FINAL REPORT")
    print("=" * 70)
    
    # load all the main analysis outputs from earlier pipeline steps
    print("\nLoading data sources...")
    
    sensitivity_df = load_csv_if_exists(sensitivity_path)
    print(f"  Sensitivity scores: {len(sensitivity_df)} videos")
    
    comments_df = load_csv_if_exists(comments_summary_path)
    print(f"  Comments analysis: {len(comments_df)} videos")
    
    algospeak_df = load_csv_if_exists(algospeak_summary_path)
    print(f"  Algospeak findings: {len(algospeak_df)} videos")
    
    input_df = load_input_csv(base_dir)
    print(f"  Input CSV: {len(input_df)} videos")
    
    # sensitivity analysis is treated as the core dataset
    # if it does not exist, the final report cannot be built properly
    if sensitivity_df.empty:
        print("\nERROR: No sensitivity analysis data found.")
        print("Please run step3_sensitivity_analysis.py first")
        sys.exit(1)
    
    # start the main combined table using sensitivity results as the base
    master_df = sensitivity_df.copy()
    
    # merge comments analysis into the master table
    # avoid duplicating the title column if it already exists
    if not comments_df.empty:
        comments_cols = [c for c in comments_df.columns if c != 'title']
        if 'video_id' in comments_cols:
            master_df = master_df.merge(
                comments_df[comments_cols],
                on='video_id',
                how='left'
            )
    
    # merge algospeak summary results into the master table
    # only keep the aggregate columns that are useful for the final report
    if not algospeak_df.empty:
        algospeak_cols = ['video_id', 'total_algospeak_instances', 'unique_terms_found']
        available_cols = [c for c in algospeak_cols if c in algospeak_df.columns]
        if available_cols:
            master_df = master_df.merge(
                algospeak_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # merge ad status from the original input csv if it is not already there
    # this is useful if ad_status was manually annotated outside the sensitivity file
    if 'ad_status' not in master_df.columns and not input_df.empty and 'url' in input_df.columns:
        input_df['video_id'] = input_df['url'].apply(extract_video_id_from_url)
        input_cols = ['video_id', 'ad_status']
        available_cols = [c for c in input_cols if c in input_df.columns]

        # only merge if there is at least one extra column besides video_id
        if len(available_cols) > 1:
            master_df = master_df.merge(
                input_df[available_cols],
                on='video_id',
                how='left'
            )
    
    # create extra fields that make the final report easier to read
    print("\nCalculating derived fields...")
    
    # calculate upload age from published_at
    if 'published_at' in master_df.columns:
        age_data = master_df['published_at'].apply(calculate_upload_age)
        master_df['upload_age'] = [a[0] for a in age_data]
        master_df['upload_age_type'] = [a[1] for a in age_data]
    
    # convert youtube ISO 8601 duration strings into a cleaner readable format
    if 'duration' in master_df.columns:
        master_df['duration_formatted'] = master_df['duration'].apply(
            lambda x: format_duration(parse_duration(x)) if pd.notna(x) else ''
        )
    
    # replace missing values with blank strings
    # this makes the excel output cleaner and easier to inspect manually
    master_df = master_df.fillna('')
    
    # define the most important columns that should appear first in the final sheet
    priority_cols = [
        'video_id', 'title', 'channel_name', 'published_at',
        'duration_formatted', 'upload_age', 'upload_age_type',
        'view_count', 'like_count', 'comment_count',
        'total_words', 'sensitive_count', 'sensitive_ratio', 'classification',
        'ad_status'
    ]
    
    # keep priority columns first, then append any remaining columns after them
    ordered_cols = [c for c in priority_cols if c in master_df.columns]
    remaining_cols = [c for c in master_df.columns if c not in ordered_cols]
    master_df = master_df[ordered_cols + remaining_cols]
    
    # write the final excel workbook
    # using multiple sheets makes it easier to inspect both the combined data
    # and the original analysis outputs separately
    print(f"\nWriting Excel report: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # main combined analysis sheet
        master_df.to_excel(writer, sheet_name='Main Analysis', index=False)
        
        # raw sensitivity analysis sheet
        if not sensitivity_df.empty:
            sensitivity_df.to_excel(writer, sheet_name='Sensitivity Details', index=False)
        
        # comments analysis sheet
        if not comments_df.empty:
            comments_df.to_excel(writer, sheet_name='Comments Analysis', index=False)
        
        # algospeak summary sheet
        if not algospeak_df.empty:
            algospeak_df.to_excel(writer, sheet_name='Algospeak Findings', index=False)
        
        # build a short summary sheet with key metrics for quick interpretation
        summary_metrics = [
            ('Total Videos', len(master_df)),
            ('Average Sensitive Ratio %', round(master_df['sensitive_ratio'].mean(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Min Sensitive Ratio %', round(master_df['sensitive_ratio'].min(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Max Sensitive Ratio %', round(master_df['sensitive_ratio'].max(), 2) if 'sensitive_ratio' in master_df.columns else 'N/A'),
            ('Likely Monetised', len(master_df[master_df['classification'] == 'Likely Monetised']) if 'classification' in master_df.columns else 'N/A'),
            ('Uncertain', len(master_df[master_df['classification'] == 'Uncertain']) if 'classification' in master_df.columns else 'N/A'),
            ('Likely Demonetised', len(master_df[master_df['classification'] == 'Likely Demonetised']) if 'classification' in master_df.columns else 'N/A'),
        ]
        
        # if algospeak data exists, count how many videos contain at least one algospeak instance
        if 'total_algospeak_instances' in master_df.columns:
            algospeak_videos = len(master_df[master_df['total_algospeak_instances'] > 0])
            summary_metrics.append(('Videos with Algospeak', algospeak_videos))
        
        # if perception comment data exists, sum the total across all videos
        if 'perception_comments' in master_df.columns:
            perception_sum = pd.to_numeric(master_df['perception_comments'], errors='coerce').sum()
            summary_metrics.append(('Total Perception Comments', int(perception_sum) if not pd.isna(perception_sum) else 0))
        
        # convert summary metrics into a dataframe and save as its own sheet
        summary_df = pd.DataFrame(summary_metrics, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
    
    # final success messages so the user knows the report was created properly
    print("\nSUCCESS: Excel report generated")
    print(f"Report saved to: {output_path}")
    print("Sheets: Main Analysis, Sensitivity Details, Comments Analysis, Algospeak Findings, Summary Statistics")
    print("Next: Run step7_visualizations.py")


if __name__ == "__main__":
    main()