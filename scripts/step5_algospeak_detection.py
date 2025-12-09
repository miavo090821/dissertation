# Step 5: Algospeak Detection (RQ3)

# Detect coded language (algospeak) in transcripts and comments.
# Uses word boundary matching to avoid false positives.
# Separates creator vs viewer usage.

import sys
import os
import csv
import json
import re
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, ALGOSPEAK_FINDINGS_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

from scripts.utils.algospeak_dict import (
    ALGOSPEAK_DICT,
    ALGOSPEAK_CATEGORIES,
    get_category
)

def get_extracted_videos(raw_dir: str) -> list:
    # Get list of video IDs that have valid extracted transcripts.
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        if os.path.isdir(item_path):
            # Check for transcript OR comments
            has_transcript = os.path.exists(os.path.join(item_path, 'transcript.txt'))
            has_comments = os.path.exists(os.path.join(item_path, 'comments.json'))
            if has_transcript or has_comments:
                video_ids.append(item)
    
    return sorted(video_ids)
                
def load_transcript(raw_dir: str, video_id: str) -> str:
    # Load transcript text for a video.
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    # If file exists, read and return its content
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Return empty string if missing
    return ""


def load_comments(raw_dir: str, video_id: str) -> list:
    # Load comments for a video.
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # Flatten to include replies
        all_comments = []
        for comment in comments:
            all_comments.append(comment)
            for reply in comment.get('replies', []):
                all_comments.append(reply)
        return all_comments
    return []

    
def load_metadata(raw_dir: str, video_id: str) -> dict:
    # Load metadata for a video.
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} 

   
def detect_algospeak_with_boundaries(text: str) -> list:
# Detect algospeak terms using word boundaries to reduce false positives.
# Returns list of dicts: {term, meaning, category, count, contexts}
    
    if not text:
        return []
    
    text_lower = text.lower()
    results = []
def archive_output(output_dir: str) -> str:
    # Archive existing output folder with timestamp.
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        return None    
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = os.path.join(archive_dir, f'output_backup_{timestamp}')
    os.rename(output_dir, archive_path)
    os.makedirs(output_dir, exist_ok=True)
    return archive_path
    # Load metadata JSON for a video if available.
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')        

def main():
    parser = argparse.ArgumentParser(description='Detect algospeak in transcripts and comments')
    parser.add_argument('--archive', action='store_true', help='Archive previous output before running')
    args = parser.parse_args()
    
    # Setup paths
    # Archive if requested
    if args.archive:
        archive_path = archive_output(output_dir)
        if archive_path:
            print(f"[ARCHIVED] Previous output saved to: {archive_path}")
    
    # Get videos
    video_ids = get_extracted_videos(raw_dir)