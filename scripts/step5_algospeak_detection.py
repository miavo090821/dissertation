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
                
def load_transcript(raw_dir: str, video_id: str) -> str:
    """Load transcript text for a video."""
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    # If file exists, read and return its content
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Return empty string if missing
    return ""


def load_comments(raw_dir: str, video_id: str) -> list:
    """Load comments for a video."""
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            return json.load(f) 
    return []
    
def load_metadata(raw_dir: str, video_id: str) -> dict:
    
def detect_algospeak_with_boundaries(text: str) -> list:
    
def archive_output(output_dir: str) -> str:
    
def main():