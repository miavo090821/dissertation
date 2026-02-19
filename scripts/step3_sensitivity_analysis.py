# Step 3: Sensitivity Analysis

# Analyze all extracted transcripts for sensitive word content.
# Calculates sensitive term ratio and classifies monetization likelihood.

import sys
import os
import csv
import json
from datetime import datetime

# Add parent directory to the import path so config and utils can be imported correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required configuration paths and filenames
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR, DICTIONARIES_DIR, SENSITIVITY_SCORES_FILE
except ImportError:
    # Stop execution if config is missing
    print("ERROR: config.py not found!")
    sys.exit(1)

# Import helper functions for transcript analysis and monetisation classification
from scripts.utils.nlp_processor import (
    analyze_transcript,
    classify_monetization
)


def get_extracted_videos(raw_dir: str) -> list:
    """Get list of video IDs that have valid extracted transcripts."""
    # Ensure directory exists
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    # Loop through each folder inside the raw data directory
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        # Each video has its own subdirectory
        if os.path.isdir(item_path):
            # Check whether a transcript file exists for this video
            transcript_path = os.path.join(item_path, 'transcript.txt')
            if os.path.exists(transcript_path):
                video_ids.append(item)
    
    # Sort video IDs alphabetically for predictable processing order
    return sorted(video_ids)


def load_metadata(raw_dir: str, video_id: str) -> dict:
    """Load metadata JSON for a video if available."""
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    # If file exists, read and return it
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Return empty metadata if missing
    return {}


def load_transcript(raw_dir: str, video_id: str) -> str:
    """Load transcript text for a video."""
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    # Read transcript if available
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Return empty string if missing
    return ""


def main():
    # Define base directories for input and output
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dict_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    
    # Path to sensitive words dictionary
    sensitive_words_path = os.path.join(dict_dir, 'sensitive_words.json')
    # Output CSV where results will be saved
    output_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    
    # Ensure sensitive words dictionary exists
    if not os.path.exists(sensitive_words_path):
        print(f"ERROR: Sensitive words dictionary not found: {sensitive_words_path}")
        print("Please ensure dictionaries/sensitive_words.json exists")
        sys.exit(1)
    
    # Load ad_status from input CSV for lookup by video_id
    import re
    ad_status_lookup = {}
    input_csv_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')
    if os.path.exists(input_csv_path):
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '')
                match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
                if match:
                    ad_status_lookup[match.group(1)] = row.get('ad_status', '')

    # Collect list of extracted videos to analyse
    video_ids = get_extracted_videos(raw_dir)
    
    # Stop execution if no data found
    if not video_ids:
        print("ERROR: No extracted videos found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    # Start logging
    print("STEP 3: SENSITIVITY ANALYSIS")
    print(f"Videos: {len(video_ids)} | Dictionary: {sensitive_words_path}\n")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    results = []
    
    # Process each video one by one
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing: {video_id}")
        
        # Load metadata and transcript
        metadata = load_metadata(raw_dir, video_id)
        transcript = load_transcript(raw_dir, video_id)
        
        # Skip if transcript missing
        if not transcript:
            print("  SKIP: No transcript")
            continue
        
        # Analyse transcript to identify sensitive content
        analysis = analyze_transcript(transcript, sensitive_words_path)
        # Classify monetisation likelihood based on ratio score
        classification = classify_monetization(analysis['sensitive_ratio'])
        
        # Prepare structured result row for CSV
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
            'ad_status': ad_status_lookup.get(video_id, '')
        }
        
        results.append(result)
        
        # Display summary of analysis for this video
        print(f"  Words: {analysis['total_words']:,} | Hits: {analysis['sensitive_count']} | "
              f"Risk: {analysis['sensitive_ratio']:.2f}% | {classification}")
    
    # Save results to CSV if any videos were processed
    if results:
        fieldnames = list(results[0].keys())
        
        # Write all result rows to the CSV output
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        # Final summary logs
        print("\nSUCCESS: Sensitivity analysis complete")
        print(f"Results saved to: {output_path}")
        print(f"Videos analysed: {len(results)}")
        
        # Collect statistics for sensitivity scores
        ratios = [r['sensitive_ratio'] for r in results]
        classifications = [r['classification'] for r in results]
        
        print(f"\nSummary: Avg Risk {sum(ratios)/len(ratios):.2f}% | "
              f"Min {min(ratios):.2f}% | Max {max(ratios):.2f}%")
        print(f"Classification: Monetised {classifications.count('Likely Monetised')} | "
              f"Uncertain {classifications.count('Uncertain')} | "
              f"Demonetised {classifications.count('Likely Demonetised')}")
        print("Next: Run step4_comments_analysis.py")
    else:
        # No rows produced
        print("ERROR: No results to save")


if __name__ == "__main__":
    main()
