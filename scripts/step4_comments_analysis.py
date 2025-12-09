# Step 4: Comments Analysis (RQ2 - Perception)

# Search comments for keywords related to monetization perception.
# Uses word boundary matching to avoid false positives.
# Separates creator comments from viewer comments.
import sys
import os
import csv
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def load_perception_keywords(dictionaries_dir: str) -> dict:
    with open(os.path.join(dictionaries_dir, 'perception_keywords.json'), 'r', encoding='utf-8') as f:
        return json.load(f)         
try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DICTIONARIES_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)     
from scripts.utils.nlp_processor import analyze_comments_perception

def get_extracted_videos(raw_dir: str) -> list:
    # Get list of video IDs that have been extracted.
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    for entry in os.listdir(raw_dir):
        video_path = os.path.join(raw_dir, entry)
        if os.path.isdir(video_path):
            video_ids.append(entry)
    return video_ids

def load_comments(raw_dir: str, video_id: str) -> list:
    # Load comments for a video.
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            return json.load(f) 
    return []

def load_metadata(raw_dir: str, video_id: str) -> dict:
    # Load metadata for a video.
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f) 
    return {}


def search_comment_with_word_boundaries(text: str, keywords_dict: dict) -> list:
    """Search for keywords in text using word boundary matching."""
    import re
    found_keywords = []
    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                found_keywords.append((category, keyword))
    return found_keywords

def main():
    print("STEP 4: COMMENTS ANALYSIS (RQ2 - PERCEPTION)\n")
    
    perception_keywords = load_perception_keywords(DICTIONARIES_DIR)
    
    output_file = os.path.join(DATA_OUTPUT_DIR, 'comments_perception_analysis.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['video_id', 'total_comments', 'creator_comments', 'viewer_comments', 'creator_positive', 'creator_negative', 'viewer_positive', 'viewer_negative']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        raw_data_dir = os.path.join(DATA_RAW_DIR)
        for video_id in os.listdir(raw_data_dir):
            video_dir = os.path.join(raw_data_dir, video_id)
            comments_file = os.path.join(video_dir, 'comments.json')
            
            if not os.path.isfile(comments_file):
                print(f"  Comments not found for video {video_id}, skipping.")
                continue
            
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments_data = json.load(f)
            
            analysis = analyze_comments_perception(comments_data, perception_keywords)
            
            writer.writerow({
                'video_id': video_id,
                'total_comments': analysis['total_comments'],
                'creator_comments': analysis['creator_comments'],
                'viewer_comments': analysis['viewer_comments'],
                'creator_positive': analysis['creator_positive'],
                'creator_negative': analysis['creator_negative'],
                'viewer_positive': analysis['viewer_positive'],
                'viewer_negative': analysis['viewer_negative']
            })
            
            print(f"  Processed comments for video {video_id}")
    
    print("\nComments perception analysis completed.")
if __name__ == "__main__":
    main()      
    