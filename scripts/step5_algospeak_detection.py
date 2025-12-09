# Entry point for Step 5: detecting algospeak in transcripts and comments

# This script detects coded language used by creators or viewers
# It scans transcripts and comments using word-boundary matching
# It supports archiving previous outputs when requested by the user

import sys
import os
import csv
import json
import re
import argparse
from datetime import datetime

# Add parent directory to allow imports from config and utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import relevant directories and output file names
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, ALGOSPEAK_FINDINGS_FILE
except ImportError:
    # Exit early if configuration is missing
    print("ERROR: config.py not found!")
    sys.exit(1)

# Import algospeak dictionary utilities
from scripts.utils.algospeak_dict import (
    ALGOSPEAK_DICT,
    ALGOSPEAK_CATEGORIES,
    get_category
)


def get_extracted_videos(raw_dir: str) -> list:
    # Return video IDs that contain transcripts or comments
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        if os.path.isdir(item_path):
            # Check if transcripts or comments exist
            has_transcript = os.path.exists(os.path.join(item_path, 'transcript.txt'))
            has_comments = os.path.exists(os.path.join(item_path, 'comments.json'))
            if has_transcript or has_comments:
                video_ids.append(item)
    
    return sorted(video_ids)


def load_transcript(raw_dir: str, video_id: str) -> str:
    # Load transcript text for a video
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def load_comments(raw_dir: str, video_id: str) -> list:
    # Load comments and their replies
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # Flatten comment and reply structure
        all_comments = []
        for comment in comments:
            all_comments.append(comment)
            for reply in comment.get('replies', []):
                all_comments.append(reply)
        return all_comments
    
    return []


def load_metadata(raw_dir: str, video_id: str) -> dict:
    # Load metadata such as title, channel ID, publication date
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def detect_algospeak_with_boundaries(text: str) -> list:
    # Detect algospeak terms with boundary-safe matching
    # Returns structured findings including term, category, count, and contexts
    if not text:
        return []
    
    text_lower = text.lower()
    results = []
    
    for term, meaning in ALGOSPEAK_DICT.items():
        term_lower = term.lower()
        
        # Build regex for matching phrases or single words
        if ' ' in term_lower or '-' in term_lower:
            pattern = re.escape(term_lower)
        else:
            pattern = r'\b' + re.escape(term_lower) + r'\b'
        
        matches = list(re.finditer(pattern, text_lower))
        count = len(matches)
        
        if count > 0:
            # Extract context windows around matches
            contexts = []
            for match in matches[:3]:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippet = text[start:end].replace('\n', ' ').strip()
                
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                contexts.append(snippet)
            
            results.append({
                'term': term,
                'meaning': meaning,
                'category': get_category(term),
                'count': count,
                'contexts': contexts
            })
    
    # Sort results by frequency in descending order
    return sorted(results, key=lambda x: x['count'], reverse=True)


def archive_output(output_dir: str) -> str:
    # Archive existing output folder by copying it into a timestamped archive directory
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        return None
    
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = os.path.join(archive_dir, f'run_{timestamp}')
    
    # Perform deep copy
    import shutil
    shutil.copytree(output_dir, archive_path)
    
    return archive_path


def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Detect algospeak in transcripts and comments')
    parser.add_argument('--archive', action='store_true', help='Archive previous output before running')
    args = parser.parse_args()
    
    # Prepare directory paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_path = os.path.join(output_dir, ALGOSPEAK_FINDINGS_FILE)
    
    # Optionally archive previous output
    if args.archive:
        archive_path = archive_output(output_dir)
        if archive_path:
            print(f"[ARCHIVED] Previous output saved to: {archive_path}")
    
    # Collect all videos that have transcripts or comments
    video_ids = get_extracted_videos(raw_dir)
    
    if not video_ids:
        print("ERROR: No extracted videos found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    print("STEP 5: ALGOSPEAK DETECTION")
    print(f"Videos: {len(video_ids)} | Algospeak terms: {len(ALGOSPEAK_DICT)}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    all_findings = []
    video_summaries = []
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Scanning: {video_id}")
        
        transcript = load_transcript(raw_dir, video_id)
        comments = load_comments(raw_dir, video_id)
        metadata = load_metadata(raw_dir, video_id)
        channel_id = metadata.get('channel_id', '')
        creator_comment_instances = 0   
        transcript_instances = 0
        transcript_unique = 0
        comment_instances = 0
        comment_unique = 0
        
        # Process transcript for algospeak
        if transcript:
            transcript_findings = detect_algospeak_with_boundaries(transcript)
            transcript_instances = sum(f['count'] for f in transcript_findings)
            transcript_unique = len(transcript_findings)
        
        # Process comments for algospeak
        comment_term_counts = {}
        
        for comment in comments:
            text = comment.get('text', '')
            is_creator = comment.get('author_channel_id', '') == channel_id
            
            comment_findings = detect_algospeak_with_boundaries(text)
            
            for term_data in comment_findings:
                term = term_data['term']
                comment_term_counts[term] = comment_term_counts.get(term, 0) + term_data['count']
                
                if is_creator:
                    creator_comment_instances += term_data['count']
                
                for context in term_data.get('contexts', ['No context']):
                    all_findings.append({
                        'video_id': video_id,
                        'video_title': metadata.get('title', '')[:50],
                        'source': 'comment',
                        'is_creator': is_creator,
                        'algospeak_term': term_data['term'],
                        'original_meaning': term_data['meaning'],
                        'category': term_data['category'],
                        'occurrences': term_data['count'],
                        'context': context
                    })
        
        comment_instances = sum(comment_term_counts.values())
        comment_unique = len(comment_term_counts)
        
        print(f"  Transcript: {transcript_instances} instances ({transcript_unique} unique)")
        print(f"  Comments: {comment_instances} instances ({comment_unique} unique, creator: {creator_comment_instances})")
    
    # Write detailed findings to CSV
    if all_findings:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_findings[0].keys()))
            writer.writeheader()
            writer.writerows(all_findings)
        print(f"\nSUCCESS: Detailed findings saved to {output_path}")
    
    # Write summary CSV
    summary_path = output_path.replace('.csv', '_summary.csv')
    if video_summaries:
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(video_summaries[0].keys()))
            writer.writeheader()
            writer.writerows(video_summaries)
        print(f"SUCCESS: Video summary saved to {summary_path}")
    
    # Compute totals across all videos
    total_transcript = sum(v['transcript_instances'] for v in video_summaries)
    total_comment = sum(v['comment_instances'] for v in video_summaries)
    total_creator_comment = sum(v['creator_comment_instances'] for v in video_summaries)
    
    print(f"\nSummary: {len(video_summaries)} videos | Transcript: {total_transcript} | Comments: {total_comment}")
    print(f"Creator comments: {total_creator_comment} | Viewer comments: {total_comment - total_creator_comment}")
    print("Next: Run step6_generate_report.py")

if __name__ == "__main__":
    # Execute script logic
    main()
