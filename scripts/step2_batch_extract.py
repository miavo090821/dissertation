# Step 2: Batch Extract All Videos

# Process all videos from video_urls.csv using YouTube Data API v3 and Supadata API.
# Extracts metadata, transcripts, and comments with replies for all videos.


import sys
import os
import json
import re
import csv
import time
import argparse
import requests


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

try:
    from config import YOUTUBE_API_KEY, DATA_RAW_DIR, DATA_INPUT_DIR, MAX_COMMENTS_PER_VIDEO, SUPADATA_API_KEY, SUPADATA_BASE_URL
except ImportError as e:
    print(f"ERROR: Could not import config.py")
    print(f"Expected location: {os.path.join(base_dir, 'config.py')}")
    print(f"Make sure you're running from the dissertation directory")
    sys.exit(1)
except SystemExit:
    raise
except Exception as e:
    print(f"ERROR: config.py found but failed to load: {e}")
    sys.exit(1)
    
def extract_video_id(url_or_id: str) -> str:
    # Extract video ID from URL or return as-is.
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

def get_video_metadata(youtube, video_id: str) -> dict:
    # Fetch video metadata using YouTube Data API.
    try:
        print(f"    Fetching metadata from YouTube API...", end="", flush=True)
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=video_id
        )
        response = request.execute()
        print(" done", flush=True)
        items = response.get("items", [])
        if response['items']:
            item = response['items'][0]
            snippet = item['snippet']
            stats = item['statistics']
            content = item['contentDetails']
            return {
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'channel_id': snippet.get('channelId', ''),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId', ''),
                'duration': content.get('duration', ''),
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'comment_count': int(stats.get('commentCount', 0)),
                'privacy_status': item.get('status', {}).get('privacyStatus', ''),
                'made_for_kids': item.get('status', {}).get('madeForKids', False)
            }
        return items[0]
    except Exception as e:
        print(f"    Metadata error: {e}")
    return None

def get_transcript_supadata(video_id: str) -> tuple:
    # Fetch transcript using Supadata API.
    url = f"https://www.youtube.com/watch?v={video_id}"
    params = {
        "url": url,
        "lang": "en",
        "text": "true",
        "mode": "native"
    }
    headers = {"x-api-key": SUPADATA_API_KEY}
    try:
        print(f"    Fetching transcript from Supadata API...", end="", flush=True)
        response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=15)
        print(" done", flush=True)        
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
        transcript = data.get("transcript", "")
        
        print(" done", flush=True)
        return transcript, data
    except Exception as e:
        print(f"    ERROR: Failed to fetch transcript for video ID {video_id}: {e}")
        return "", {}           

def get_comments_with_replies(youtube, video_id: str, max_comments: int = 200) -> list:
    # Fetch comments with replies using YouTube Data API.
    comments = []
    next_page_token = None
    
def load_video_list(input_dir: str) -> list:
    # Load video URLs from CSV.
    csv_path = os.path.join(input_dir, 'video_urls.csv')

    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found!")
        sys.exit(1)
        
    videos = []
def main():
    parser = argparse.ArgumentParser(description='Batch extract video data')
    parser.add_argument('--skip-existing', action='store_true', help='Skip videos with existing data')
    parser.add_argument('--transcript-delay', type=int, default=3, help='Delay between transcript fetches (default: 3s)')
    
    # Load video list
    # Stats
    
if __name__ == "__main__":
    main()
