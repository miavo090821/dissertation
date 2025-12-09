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
    """
    Fetch video transcript using youtube-transcript-api.
    
    Includes retry logic with exponential backoff for rate limiting (429 errors).
    
    Args:
        video_id: YouTube video ID
        max_retries: Number of retries on rate limit errors
        
    Returns:
        Tuple of (transcript_text, transcript_segments)
        - transcript_text: Full transcript as plain text
        - transcript_segments: List of dicts with 'start', 'duration', 'text'
        
    Returns (None, None) if transcript unavailable.
    """
    import time
    
    segments = None
    last_error = None
    
    for attempt in range(max_retries):
        if attempt > 0:
            # Exponential backoff: 5s, 10s, 20s
            wait_time = 5 * (2 ** (attempt - 1))
            print(f"  [RETRY] Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)
        
        # Method 1: Direct get_transcript() - simplest and most reliable
        try:
            segments = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
            break  # Success!
        except Exception as e:
            last_error = e
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue  # Rate limited, will retry
        
        # Method 2: Try list_transcripts approach
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try auto-generated specifically (most common)
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                segments = transcript.fetch()
                break  # Success!
            except Exception:
                # Try manual transcripts
                try:
                    transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
                    segments = transcript.fetch()
                    break  # Success!
                except Exception:
                    # Last resort: any available transcript
                    available = list(transcript_list)
                    if available:
                        segments = available[0].fetch()
                        break  # Success!
        except Exception as e:
            last_error = e
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue  # Rate limited, will retry
    
    if not segments:
        error_msg = str(last_error) if last_error else "Unknown error"
        if '429' in error_msg or 'Too Many Requests' in error_msg:
            print(f"  [WARNING] Rate limited by YouTube for {video_id}. Try again later.")
        else:
            print(f"  [WARNING] Could not retrieve transcript for {video_id}: {error_msg[:100]}")
        return None, None
    
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
    # Fetch video comments from YouTube API.
    
    # Uses pagination to fetch more than the default 20/100 limit.
    
    # Args:
    #     api_key: YouTube Data API v3 key
    #     video_id: YouTube video ID
    #     max_comments: Maximum number of comments to fetch
        
    # Returns:
    #     List of comment dictionaries containing:
    #     - author: str
    #     - author_channel_id: str
    #     - text: str
    #     - like_count: int
    #     - published_at: str
    #     - updated_at: str

    youtube = get_youtube_client(api_key)
    comments = []
    next_page_token = None
    
    try:
        while len(comments) < max_comments:
            # Fetch up to 100 per request (API max)
            fetch_count = min(100, max_comments - len(comments))
            
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=fetch_count,
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )
            response = request.execute()
                
    except Exception as e:
        # Comments might be disabled
        if "commentsDisabled" in str(e):
            print(f"  [INFO] Comments are disabled for {video_id}")
        else:
            print(f"  [WARNING] Error fetching comments for {video_id}: {e}")
    
    return comments

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
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds
    
def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
 
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

