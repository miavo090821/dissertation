# Step 2: Batch Extract All Videos

# Process all videos from video_urls.csv using YouTube Data API v3 and Supadata API.
# Extracts metadata, transcripts, and comments with replies for all videos.


import sys
import os
import json


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