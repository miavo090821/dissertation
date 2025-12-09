# YouTube API Helper Functions
# Handles all interactions with YouTube Data API v3 and youtube-transcript-api


import re
import json
import os
from datetime import datetime
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_id(url: str) -> str:

    # Extract video ID from various YouTube URL formats.
    
    # Supports:
    # - https://www.youtube.com/watch?v=VIDEO_ID
    # - https://youtu.be/VIDEO_ID
    # - https://www.youtube.com/embed/VIDEO_ID
    # - https://www.youtube.com/v/VIDEO_ID
    
    # Args:
    #     url: YouTube video URL
        
    # Returns:
    #     11-character video ID
        
    # Raises:
    #     ValueError: If video ID cannot be extracted

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"  # Direct video ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract video ID from: {url}")

def get_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)

def get_video_metadata(api_key: str, video_id: str) -> dict:
    try:
        youtube = get_youtube_client(api_key)
        
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            print(f"  [WARNING] No video found for ID: {video_id}")
            return None
        
        item = response['items'][0]
        snippet = item['snippet']
        stats = item['statistics']
        content = item['contentDetails']
        
        return {}
        
    except Exception as e:
        print(f"  [ERROR] Failed to fetch metadata for {video_id}: {e}")
        return None

def get_channel_info(api_key: str, channel_id: str) -> dict:

def get_video_transcript(video_id: str, max_retries: int = 3) -> tuple:
    import time
    
    segments = None
    last_error = None
    
    for attempt in range(max_retries):
        if attempt > 0:
            # Exponential backoff: 5s, 10s, 20s
            wait_time = 5 * (2 ** (attempt - 1))
            print(f"  [RETRY] Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)
            
            # Process segments - handle both dict and object formats
    full_text_parts = []
    processed_segments = []
    
    for seg in segments:
        try:
            start = seg['start'] if isinstance(seg, dict) else seg.start
            duration = seg['duration'] if isinstance(seg, dict) else seg.duration
            text = seg['text'] if isinstance(seg, dict) else seg.text
        except (KeyError, AttributeError):
            continue
        
        full_text_parts.append(text)
        processed_segments.append({
            'start': start,
            'duration': duration,
            'text': text
        })
    
    full_text = ' '.join(full_text_parts)
    return full_text, processed_segments

def get_video_comments(api_key: str, video_id: str, max_comments: int = 200) -> list:
    youtube = get_youtube_client(api_key)
    comments = []
    next_page_token = None
def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
def format_duration(seconds: int) -> str:
 
 
def save_video_data(output_dir: str, video_id: str, metadata: dict, 
                    transcript_text: str, transcript_segments: list, 
                    comments: list) -> None:   
    # Save all extracted video data to files.
    
    # Creates a folder structure:
    # output_dir/
    #     video_id/
    #         metadata.json
    #         transcript.txt
    #         transcript_segments.json
    #         comments.json
    
    # Args:
    #     output_dir: Base output directory
    #     video_id: YouTube video ID
    #     metadata: Video metadata dictionary
    #     transcript_text: Plain text transcript
    #     transcript_segments: List of transcript segments
    #     comments: List of comment dictionaries
        
    video_dir = os.path.join(output_dir, video_id)
    os.makedirs(video_dir, exist_ok=True)
    
    # Save metadata
    if metadata:
        with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Save transcript text
    if transcript_text:
        with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
            f.write(transcript_text)
    
    # Save transcript segments
    if transcript_segments:
        with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
            json.dump(transcript_segments, f, indent=2, ensure_ascii=False)
    
    # Save comments
    if comments:
        with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2, ensure_ascii=False)
    
    print(f"  [SAVED] Data saved to {video_dir}")

