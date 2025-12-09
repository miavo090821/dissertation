# Step 4: Comments Analysis (RQ2 - Perception)

# Search comments for keywords related to monetization perception.
# Uses word boundary matching to avoid false positives.
# Separates creator comments from viewer comments.
import sys
import os
import csv
import json
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DICTIONARIES_DIR, COMMENTS_ANALYSIS_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)


def load_perception_keywords(dictionaries_dir: str) -> dict:
    """Load perception keywords from JSON file."""
    keywords_path = os.path.join(dictionaries_dir, 'perception_keywords.json')
    
    if not os.path.exists(keywords_path):
        print(f"WARNING: {keywords_path} not found")
        return {}
    
    with open(keywords_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract keywords from nested structure
    keywords_dict = {}
    categories = data.get('categories', data)
    
    for category_name, category_data in categories.items():
        if isinstance(category_data, dict) and 'keywords' in category_data:
            keywords_dict[category_name] = category_data['keywords']
        elif isinstance(category_data, list):
            keywords_dict[category_name] = category_data
    
    return keywords_dict


def get_extracted_videos(raw_dir: str) -> list:
    """Get list of video IDs that have comments extracted."""
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
    """Load comments for a video, including replies."""
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        all_comments = []
        for comment in comments:
            all_comments.append(comment)
            all_comments.extend(comment.get('replies', []))
        
        return all_comments
    
    return []

def load_metadata(raw_dir: str, video_id: str) -> dict:
    """Load metadata for a video."""
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {}


def search_comment_with_word_boundaries(text: str, keywords_dict: dict) -> list:
    """
    Search comment text for perception keywords using word boundaries.
    Uses regex word boundaries to avoid false positives.
    Returns list of (category, matched_keyword) tuples.
    """
    text_lower = text.lower()
    matches = []
    
    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            if ' ' in keyword_lower or '-' in keyword_lower:
                if keyword_lower in text_lower:
                    matches.append((category, keyword))
            else:
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, text_lower):
                    matches.append((category, keyword))
    
    return matches


def is_creator_comment(comment: dict, channel_id: str) -> bool:
    """Check if comment is from the channel owner."""
    author_channel_id = comment.get('author_channel_id', '')
    return author_channel_id == channel_id


def main():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dictionaries_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    output_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE)
    
    # Load keywords from JSON file
    PERCEPTION_KEYWORDS = load_perception_keywords(dictionaries_dir)
    
    if not PERCEPTION_KEYWORDS:
        print("ERROR: No perception keywords loaded")
        print(f"Check: {os.path.join(dictionaries_dir, 'perception_keywords.json')}")
        sys.exit(1)
    
    # Get videos
    video_ids = get_extracted_videos(raw_dir)
    
    if not video_ids:
        print("ERROR: No videos with comments found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    print("STEP 4: COMMENTS PERCEPTION ANALYSIS")
    total_keywords = sum(len(kw) for kw in PERCEPTION_KEYWORDS.values())
    print(f"Videos: {len(video_ids)} | Categories: {len(PERCEPTION_KEYWORDS)} | Keywords: {total_keywords}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    all_matches = []
    video_summaries = []
    total_creator_comments = 0
    total_creator_matches = 0
    total_viewer_comments = 0
    total_viewer_matches = 0
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing comments: {video_id}")
        
        comments = load_comments(raw_dir, video_id)
        metadata = load_metadata(raw_dir, video_id)
        channel_id = metadata.get('channel_id', '')
        channel_name = metadata.get('channel_name', '')
        
        if not comments:
            print(f"  SKIP: No comments")
            continue
        
        for comment in comments:
            text = comment.get('text', '')
            is_reply = comment.get('is_reply', False)
            is_creator = is_creator_comment(comment, channel_id)
            
            if is_creator:
                creator_comment_count += 1
            
            matches = search_comment_with_word_boundaries(text, PERCEPTION_KEYWORDS)
            
            if matches:
                video_matches += 1
                if is_creator:
                    creator_matches += 1
                else:
                    viewer_matches += 1
                
                categories_found = list(set([m[0] for m in matches]))
                keywords_found = list(set([m[1] for m in matches]))
                
                for cat in categories_found:
                    category_counts[cat] += 1
                
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
        print(f"  Comments: {len(comments)} (creator: {creator_comment_count}) | "
              f"Perception: {video_matches} (creator: {creator_matches}, viewers: {viewer_matches})")

if __name__ == "__main__":
    main()
