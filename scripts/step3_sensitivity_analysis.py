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
    print("STEP 3: SENSITIVITY ANALYSIS\n")
    
    sensitivity_words = load_sensitivity_words(os.path.join(DICTIONARIES_DIR, 'sensitive_words.json'))
    
    output_file = os.path.join(DATA_OUTPUT_DIR, 'sensitivity_analysis_results.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['video_id', 'sensitive_term_count', 'total_word_count', 'sensitive_term_ratio', 'monetization_classification']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        raw_data_dir = os.path.join(DATA_RAW_DIR)
        for video_id in os.listdir(raw_data_dir):
            video_dir = os.path.join(raw_data_dir, video_id)
            transcript_file = os.path.join(video_dir, 'transcript.txt')
            
            if not os.path.isfile(transcript_file):
                print(f"  Transcript not found for video {video_id}, skipping.")
                continue
            
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            analysis = analyze_transcript(transcript_text, sensitivity_words)
            classification = classify_monetization(analysis['sensitive_term_ratio'])        
            
            writer.writerow({
                'video_id': video_id,
                'sensitive_term_count': analysis['sensitive_term_count'],
                'total_word_count': analysis['total_word_count'],
                'sensitive_term_ratio': analysis['sensitive_term_ratio'],
                'monetization_classification': classification
            })  
            print(f"  Analyzed video {video_id}: Sensitive Terms={analysis['sensitive_term_count']}, Total Words={analysis['total_word_count']}, Ratio={analysis['sensitive_term_ratio']:.4f}, Classification={classification}")
            
    print(f"\nSensitivity analysis complete. Results saved to {output_file}")
    
if __name__ == "__main__":
    main()
    