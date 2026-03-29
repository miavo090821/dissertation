# step 3: sensitivity analysis
#
# 1. this script looks through all transcript files collected in step 2
# 2. it checks each transcript against a sensitive words dictionary
# 3. the goal is to estimate how much potentially risky language appears in each video
# 4. it calculates a sensitivity ratio = sensitive words found / total words
# 5. based on that ratio, the script classifies each video as likely monetised, uncertain, or likely demonetised
# 6. the results are saved to a csv so they can later be compared with real ad detection outcomes
# 7. this step is basically an early proxy test for monetisation risk before comparing against actual ad evidence

import sys   
# risk before comparing against actual ad evidence

import sys   
# used for system actions like sys.exit() if a required file is missing
import os    
# helps work with file paths, folders, and directory checks
import csv   
# used to read the input csv and write the final analysis output csv
import json  
# used to load metadata json files for each video
from datetime import datetime  
# useful for date/time handling, even though it is not heavily used here


# need this so python can find our config and utils folders one level up
# without this, imports may fail if the script is run from inside the scripts folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import shared config values used across the project
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR, DICTIONARIES_DIR, SENSITIVITY_SCORES_FILE
except ImportError:
    # stop immediately if config.py cannot be found
    print("ERROR: config.py not found!")
    sys.exit(1)

# these are helper nlp functions written in utils
# they do the actual transcript analysis and classification work
from scripts.utils.nlp_processor import (
    analyze_transcript,              
    # counts total words, sensitive hits, ratio, and found terms
    analyze_transcript_by_category,  
    # breaks sensitive hits into categories like violence, drugs, etc.
    classify_monetization            
    # turns the ratio into a label such as likely monetised or demonetised
)


def get_extracted_videos(raw_dir: str) -> list:
    """Get list of video IDs that have valid extracted transcripts."""
    
    # if the raw data folder does not exist yet, return an empty list
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []

    # go through each item inside the raw data folder
    # each video should have its own subfolder named by video id
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)

        # only continue if this item is actually a folder
        if os.path.isdir(item_path):
            # check whether this video folder contains a transcript file
            transcript_path = os.path.join(item_path, 'transcript.txt')
            if os.path.exists(transcript_path):
                video_ids.append(item)
    
    # sort video ids so processing order is stable and predictable
    return sorted(video_ids)


def load_metadata(raw_dir: str, video_id: str) -> dict:
    """Load metadata JSON for a video if available."""
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    # if metadata file exists, open and load the json
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # if metadata is missing, return an empty dictionary instead of crashing
    return {}


def load_transcript(raw_dir: str, video_id: str) -> str:
    """Load transcript text for a video."""
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    # open transcript file if it exists
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # return an empty string if transcript is missing
    return ""


def main():
    # build the main project paths relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dict_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    
    # path to the sensitive words dictionary json
    sensitive_words_path = os.path.join(dict_dir, 'sensitive_words.json')

    # path where the final sensitivity analysis csv will be saved
    output_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    
    # make sure the sensitive words dictionary exists before continuing
    if not os.path.exists(sensitive_words_path):
        print(f"ERROR: Sensitive words dictionary not found: {sensitive_words_path}")
        print("Please ensure dictionaries/sensitive_words.json exists")
        sys.exit(1)
    
    # load ad_status from input csv so we can later compare sensitivity results
    # with the actual ad detection results already stored in video_urls.csv

    import re  # imported here because it is only needed for this small lookup task

    ad_status_lookup = {}
    input_csv_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')

    if os.path.exists(input_csv_path):
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '')

                # extract the video id from the youtube url
                match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
                if match:
                    ad_status_lookup[match.group(1)] = row.get('ad_status', '')

    # collect all video ids that have extracted transcript data
    video_ids = get_extracted_videos(raw_dir)
    
    # stop if there is nothing to analyse
    if not video_ids:
        print("ERROR: No extracted videos found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    # starting log messages
    print("STEP 3: SENSITIVITY ANALYSIS")
    print(f"Videos: {len(video_ids)} | Dictionary: {sensitive_words_path}\n")
    
    # make sure output folder exists before saving results
    os.makedirs(output_dir, exist_ok=True)
    results = []
    
    # process each video one by one
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing: {video_id}")
        
        # load saved metadata and transcript for this video
        metadata = load_metadata(raw_dir, video_id)
        transcript = load_transcript(raw_dir, video_id)
        
        # skip videos that do not have transcript text
        if not transcript:
            print("  SKIP: No transcript")
            continue
        
        # run the main transcript sensitivity analysis
        # this gives total words, sensitive word hits, ratio, and found terms
        analysis = analyze_transcript(transcript, sensitive_words_path)

        # get a category-level breakdown, e.g. violence, drugs, sexual content
        category_counts = analyze_transcript_by_category(transcript, sensitive_words_path)

        # convert the numeric ratio into a monetisation-style label
        classification = classify_monetization(analysis['sensitive_ratio'])

        # build one result row for this video
        # this row will later become one row in the output csv
        result = {
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'channel_name': metadata.get('channel_name', ''),
            'published_at': metadata.get('published_at', '')[:10] if metadata.get('published_at') else '',
            'duration': metadata.get('duration', ''),
            'view_count': metadata.get('view_count', 0),
            'like_count': metadata.get('like_count', 0),
            'comment_count': metadata.get('comment_count', 0),
            'total_words': analysis['total_words'],
            'sensitive_count': analysis['sensitive_count'],
            'sensitive_ratio': analysis['sensitive_ratio'],
            'classification': classification,
            'found_terms': ', '.join(analysis['found_terms'][:10]),  

            # only keep first 10 terms so the csv stays readable
            'ad_status': ad_status_lookup.get(video_id, ''),          
            # actual ad result if available
        }

        # add the per-category counts into the same row
        # cat here just means category
        for cat_name, cat_data in category_counts.items():
            result[f'{cat_name}_count'] = cat_data['count']
        
        results.append(result)
        
        # print a short summary for this video so we can monitor progress
        print(f"  Words: {analysis['total_words']:,} | Hits: {analysis['sensitive_count']} | "
              f"Risk: {analysis['sensitive_ratio']:.2f}% | {classification}")
    
    # only save output if at least one result row was created
    if results:
        fieldnames = list(results[0].keys())
        
        # write all result rows into the output csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        # final success summary
        print("\nSUCCESS: Sensitivity analysis complete")
        print(f"Results saved to: {output_path}")
        print(f"Videos analysed: {len(results)}")
        
        # collect overall sensitivity score stats across all videos
        ratios = [r['sensitive_ratio'] for r in results]
        classifications = [r['classification'] for r in results]
        
        print(f"\nSummary: Avg Risk {sum(ratios)/len(ratios):.2f}% | "
              f"Min {min(ratios):.2f}% | Max {max(ratios):.2f}%")

        # show how many videos fell into each classification group
        print(f"Classification: Monetised {classifications.count('Likely Monetised')} | "
              f"Uncertain {classifications.count('Uncertain')} | "
              f"Demonetised {classifications.count('Likely Demonetised')}")

        print("Next: Run step4_comments_analysis.py")
    else:
        # this means nothing was processed successfully
        print("ERROR: No results to save")

if __name__ == "__main__":
    # only run main() when this script is executed directly
    # this stops it from running automatically if imported into another file
    main()