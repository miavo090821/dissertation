# Step 4: Comments Analysis (RQ2 - Perception)

# Search comments for keywords related to monetization perception.
# Uses word boundary matching to avoid false positives.
# Separates creator comments from viewer comments.
import sys
import os
import csv
import json
import re

# Add parent directory to the system path so internal modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import project-wide configuration paths and filenames
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DICTIONARIES_DIR, COMMENTS_ANALYSIS_FILE
except ImportError:
    # Exit if config is missing, since paths are required
    print("ERROR: config.py not found!")
    sys.exit(1)


def load_perception_keywords(dictionaries_dir: str) -> dict:
    # Load perception keyword categories from JSON definitions
    keywords_path = os.path.join(dictionaries_dir, 'perception_keywords.json')
    
    if not os.path.exists(keywords_path):
        # Warn if the dictionary file does not exist
        print(f"WARNING: {keywords_path} not found")
        return {}
    
    # Read JSON file
    with open(keywords_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Build keyword dictionary regardless of file structure format
    keywords_dict = {}
    categories = data.get('categories', data)
    
    for category_name, category_data in categories.items():
        # Support both simple list formats and dict-with-keywords formats
        if isinstance(category_data, dict) and 'keywords' in category_data:
            keywords_dict[category_name] = category_data['keywords']
        elif isinstance(category_data, list):
            keywords_dict[category_name] = category_data
    
    return keywords_dict


def get_extracted_videos(raw_dir: str) -> list:
    # Return all video IDs that have a comments.json file present
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        if os.path.isdir(item_path):
            comments_path = os.path.join(item_path, 'comments.json')
            if os.path.exists(comments_path):
                video_ids.append(item)
    
    return sorted(video_ids)


def load_comments(raw_dir: str, video_id: str) -> list:
    # Load comments and replies for a given video
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # Flatten comment + replies into a single list
        all_comments = []
        for comment in comments:
            all_comments.append(comment)
            all_comments.extend(comment.get('replies', []))
        
        return all_comments
    
    return []


def load_metadata(raw_dir: str, video_id: str) -> dict:
    # Load video metadata from metadata.json
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {}


def search_comment_with_word_boundaries(text: str, keywords_dict: dict) -> list:
    # Detect perception keywords in a comment using regex-safe word boundaries
    text_lower = text.lower()
    matches = []
    
    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # If keyword contains spaces or hyphens, match as substring safely
            if ' ' in keyword_lower or '-' in keyword_lower:
                if keyword_lower in text_lower:
                    matches.append((category, keyword))
            else:
                # Use regex to match whole words
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, text_lower):
                    matches.append((category, keyword))
    
    return matches


def is_creator_comment(comment: dict, channel_id: str) -> bool:
    # Determine whether the comment was written by the channel owner
    author_channel_id = comment.get('author_channel_id', '')
    return author_channel_id == channel_id


def main():
    # Build absolute paths for raw data, output, and dictionaries
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dictionaries_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    output_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE)
    
    # Load perception keyword definitions
    PERCEPTION_KEYWORDS = load_perception_keywords(dictionaries_dir)
    
    if not PERCEPTION_KEYWORDS:
        # Stop execution if keywords are not loaded
        print("ERROR: No perception keywords loaded")
        print(f"Check: {os.path.join(dictionaries_dir, 'perception_keywords.json')}")
        sys.exit(1)
    
    # Retrieve list of video IDs with extracted comments
    video_ids = get_extracted_videos(raw_dir)
    
    if not video_ids:
        print("ERROR: No videos with comments found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    # Display overview
    print("STEP 4: COMMENTS PERCEPTION ANALYSIS")
    total_keywords = sum(len(kw) for kw in PERCEPTION_KEYWORDS.values())
    print(f"Videos: {len(video_ids)} | Categories: {len(PERCEPTION_KEYWORDS)} | Keywords: {total_keywords}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Structures to store full results and aggregated summaries
    all_matches = []
    video_summaries = []
    total_creator_comments = 0
    total_creator_matches = 0
    total_viewer_comments = 0
    total_viewer_matches = 0
    
    for i, video_id in enumerate(video_ids, 1):
        # Process each video
        print(f"[{i}/{len(video_ids)}] Analyzing comments: {video_id}")
        
        comments = load_comments(raw_dir, video_id)
        metadata = load_metadata(raw_dir, video_id)
        channel_id = metadata.get('channel_id', '')
        channel_name = metadata.get('channel_name', '')
        
        if not comments:
            # Skip videos with no comments
            print(f"  SKIP: No comments")
            continue
        
        # Counters for this video
        video_matches = 0
        creator_matches = 0
        viewer_matches = 0
        creator_comment_count = 0
        category_counts = {cat: 0 for cat in PERCEPTION_KEYWORDS.keys()}
        
        for comment in comments:
            text = comment.get('text', '')
            is_reply = comment.get('is_reply', False)
            is_creator = is_creator_comment(comment, channel_id)
            
            if is_creator:
                creator_comment_count += 1
            
            # Detect perception keywords
            matches = search_comment_with_word_boundaries(text, PERCEPTION_KEYWORDS)
            
            if matches:
                video_matches += 1
                
                # Classify as creator or viewer match
                if is_creator:
                    creator_matches += 1
                else:
                    viewer_matches += 1
                
                # Extract distinct matched categories and keywords
                categories_found = list(set([m[0] for m in matches]))
                keywords_found = list(set([m[1] for m in matches]))
                
                # Count category frequencies
                for cat in categories_found:
                    category_counts[cat] += 1
                
                # Record detailed match row
                all_matches.append({
                    'video_id': video_id,
                    'video_title': metadata.get('title', '')[:50],
                    'is_creator': is_creator,
                    'is_reply': is_reply,
                    'comment_author': comment.get('author', ''),
                    'comment_likes': comment.get('like_count', 0),
                    'comment_text': text[:500].replace('\n', ' '),
                    'categories_matched': ', '.join(categories_found),
                    'keywords_matched': ', '.join(keywords_found)
                })
        
        # Update global counters
        total_creator_comments += creator_comment_count
        total_creator_matches += creator_matches
        total_viewer_comments += len(comments) - creator_comment_count
        total_viewer_matches += viewer_matches
        
        # Build summary entry for this video
        video_summaries.append({
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'channel_name': channel_name,
            'total_comments': len(comments),
            'creator_comments': creator_comment_count,
            'perception_comments': video_matches,
            'creator_perception': creator_matches,
            'viewer_perception': viewer_matches,
            'perception_ratio': round(video_matches / len(comments) * 100, 2) if comments else 0,
            **{f'{cat}_mentions': count for cat, count in category_counts.items()}
        })
        
        print(f"  Comments: {len(comments)} (creator: {creator_comment_count}) | "
              f"Perception: {video_matches} (creator: {creator_matches}, viewers: {viewer_matches})")
    
    # Write full match dataset to CSV
    if all_matches:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_matches[0].keys()))
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"\nSUCCESS: Detailed matches saved to {output_path}")
    
    # Write video-level summary CSV
    summary_path = output_path.replace('.csv', '_summary.csv')
    if video_summaries:
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(video_summaries[0].keys()))
            writer.writeheader()
            writer.writerows(video_summaries)
        print(f"SUCCESS: Video summary saved to {summary_path}")
    
    # Compute global totals
    total_perception = sum(v['perception_comments'] for v in video_summaries)
    total_comments = sum(v['total_comments'] for v in video_summaries)
    
    print(f"\nSummary: {total_comments:,} comments analyzed | {total_perception} with perception keywords")
    print(f"Creator: {total_creator_matches}/{total_creator_comments} | Viewer: {total_viewer_matches}/{total_viewer_comments:,}")
    print("Next: Run step5_algospeak_detection.py")


if __name__ == "__main__":
    # Execute main analysis pipeline when run as a script
    main()