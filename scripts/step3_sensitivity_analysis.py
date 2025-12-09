# Step 3: Sensitivity Analysis

# Analyze all extracted transcripts for sensitive word content.
# Calculates sensitive term ratio and classifies monetization likelihood.


import sys
import os
import csv
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DICTIONARIES_DIR, SENSITIVITY_SCORES_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

from scripts.utils.nlp_processor import (
    analyze_transcript,
    classify_monetization
)


def get_extracted_videos(raw_dir: str) -> list:
    # Get list of video IDs that have been extracted.
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        if os.path.isdir(item_path):
            # Check if it has a transcript
            transcript_path = os.path.join(item_path, 'transcript.txt')
            if os.path.exists(transcript_path):
                video_ids.append(item)
    
    return sorted(video_ids)


def load_metadata(raw_dir: str, video_id: str) -> dict:
    # Load metadata for a video.
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {}


def load_transcript(raw_dir: str, video_id: str) -> str:
    # Load transcript text for a video.
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    return ""

def main():
def main():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dict_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    
    sensitive_words_path = os.path.join(dict_dir, 'sensitive_words.json')
    output_path = os.path.join(output_dir, SENSITIVITY_SCORES_FILE)
    
    # Validate
    if not os.path.exists(sensitive_words_path):
        print(f"ERROR: Sensitive words dictionary not found: {sensitive_words_path}")
        print("Please ensure dictionaries/sensitive_words.json exists")
        sys.exit(1)
    
    # Get videos
    video_ids = get_extracted_videos(raw_dir)
    
    if not video_ids:
        print("ERROR: No extracted videos found")
        print(f"Please run step2_batch_extract.py first")
        sys.exit(1)
    
    print("STEP 3: SENSITIVITY ANALYSIS")
    print(f"Videos: {len(video_ids)} | Dictionary: {sensitive_words_path}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    results = []
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing: {video_id}")
        
        metadata = load_metadata(raw_dir, video_id)
        transcript = load_transcript(raw_dir, video_id)
        
        if not transcript:
            print("  SKIP: No transcript")
            continue
        
        analysis = analyze_transcript(transcript, sensitive_words_path)
        classification = classify_monetization(analysis['sensitive_ratio'])
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
            'manual_starting_ads': metadata.get('manual_starting_ads', ''),
            'manual_mid_roll_ads': metadata.get('manual_mid_roll_ads', ''),
            'manual_ad_breaks': metadata.get('manual_ad_breaks_detected', '')
        }
        
        results.append(result)
        print(f"  Words: {analysis['total_words']:,} | Hits: {analysis['sensitive_count']} | "
              f"Risk: {analysis['sensitive_ratio']:.2f}% | {classification}")
    
    if results:
        fieldnames = list(results[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print("\nSUCCESS: Sensitivity analysis complete")
        print(f"Results saved to: {output_path}")
        print(f"Videos analyzed: {len(results)}")
        
        ratios = [r['sensitive_ratio'] for r in results]
        classifications = [r['classification'] for r in results]
        
        print(f"\nSummary: Avg Risk {sum(ratios)/len(ratios):.2f}% | "
              f"Min {min(ratios):.2f}% | Max {max(ratios):.2f}%")
        print(f"Classification: Monetised {classifications.count('Likely Monetised')} | "
              f"Uncertain {classifications.count('Uncertain')} | "
              f"Demonetised {classifications.count('Likely Demonetised')}")
        print("Next: Run step4_comments_analysis.py")
    else:
        print("ERROR: No results to save")
if __name__ == "__main__":
    main()
    