# Helper utilities for YouTube data and transcript extraction
# YouTube API Helper Functions
# Handles all interactions with YouTube Data API v3 
# and youtube-transcript-api
#  for step 6
import re
import json
import os
from datetime import datetime
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# Extract a YouTube video ID from many URL formats
def get_video_id(url: str) -> str:
    # Patterns cover watch URLs, youtu.be shortlinks, embed links, and raw IDs
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]
    
    # Try each pattern until a match is found
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no match, raise an error indicating the URL is invalid
    raise ValueError(f"Could not extract video ID from: {url}")

# Build and return a YouTube Data API client
def get_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)

# Fetch metadata about a specific video
def get_video_metadata(api_key: str, video_id: str) -> dict:
    try:
        # Create API client
        youtube = get_youtube_client(api_key)
        
        # Request metadata fields from multiple parts
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        # Handle case where video does not exist or is private
        if not response.get('items'):
            print(f"  [WARNING] No video found for ID: {video_id}")
            return None
        
        # Extract core fields from the API response
        item = response['items'][0]
        snippet = item['snippet']
        stats = item['statistics']
        content = item['contentDetails']
        
        # Return cleaned and structured metadata dictionary
        return {
            'video_id': video_id,
            'title': snippet.get('title', ''),
            'channel_name': snippet.get('channelTitle', ''),
            'channel_id': snippet.get('channelId', ''),
            'description': snippet.get('description', ''),
            'published_at': snippet.get('publishedAt', ''),
            'duration': content.get('duration', ''),
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'comment_count': int(stats.get('commentCount', 0)),
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId', ''),
            'extracted_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        # Catch all failures including quota, bad keys, or network issues
        print(f"  [ERROR] Failed to fetch metadata for {video_id}: {e}")
        return None

# Fetch information about a YouTube channel
def get_channel_info(api_key: str, channel_id: str) -> dict:
    try:
        youtube = get_youtube_client(api_key)
        
        # Request subscriber count, total views, and video count
        request = youtube.channels().list(
            part="statistics,snippet",
            id=channel_id
        )
        response = request.execute()
        
        # Channel might not exist
        if not response.get('items'):
            return None
        
        # Extract statistics
        item = response['items'][0]
        stats = item['statistics']
        
        # Return cleaned info
        return {
            'channel_id': channel_id,
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'view_count': int(stats.get('viewCount', 0))
        }
        
    except Exception as e:
        print(f"  [ERROR] Failed to fetch channel info: {e}")
        return None

# Fetch transcript using youtube-transcript-api with retries
def get_video_transcript(video_id: str, max_retries: int = 3) -> tuple:
    import time
    
    segments = None
    last_error = None
    
    # Attempt multiple retries with exponential backoff
    for attempt in range(max_retries):
        if attempt > 0:
            wait_time = 5 * (2 ** (attempt - 1))
            print(f"  [RETRY] Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)
        
        # First attempt: direct transcript fetch
        try:
            segments = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB']
            )
            break
        except Exception as e:
            last_error = e
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue
        
        # Second attempt: list_transcripts approach
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try autogenerated first
            try:
                transcript = transcript_list.find_generated_transcript(
                    ['en', 'en-US', 'en-GB']
                )
                segments = transcript.fetch()
                break
            except Exception:
                pass
            
            # Try manually uploaded transcript
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    ['en', 'en-US', 'en-GB']
                )
                segments = transcript.fetch()
                break
            except Exception:
                pass
            
            # Last resort: use any transcript available
            available = list(transcript_list)
            if available:
                segments = available[0].fetch()
                break
        
        except Exception as e:
            last_error = e
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue
    
    # If no segments were retrieved, handle error cases
    if not segments:
        error_msg = str(last_error) if last_error else "Unknown error"
        
        if '429' in error_msg or 'Too Many Requests' in error_msg:
            print(f"  [WARNING] Rate limited by YouTube for {video_id}. Try again later.")
        else:
            print(f"  [WARNING] Could not retrieve transcript for {video_id}: {error_msg[:100]}")
        
        return None, None
    
    # Convert transcript segments into plain text and structured list
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

# Retrieve comments from YouTube using pagination
def get_video_comments(api_key: str, video_id: str, max_comments: int = 200) -> list:
    youtube = get_youtube_client(api_key)
    comments = []
    next_page_token = None
    
    try:
        # Fetch comments until maximum reached or no more results
        while len(comments) < max_comments:
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
            
            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                
                comments.append({
                    'author': snippet.get('authorDisplayName', ''),
                    'author_channel_id': snippet.get('authorChannelId', {}).get('value', ''),
                    'text': snippet.get('textDisplay', ''),
                    'like_count': snippet.get('likeCount', 0),
                    'published_at': snippet.get('publishedAt', ''),
                    'updated_at': snippet.get('updatedAt', '')
                })
                
                if len(comments) >= max_comments:
                    break
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
    
    except Exception as e:
        if "commentsDisabled" in str(e):
            print(f"  [INFO] Comments are disabled for {video_id}")
        else:
            print(f"  [WARNING] Error fetching comments for {video_id}: {e}")
    
    return comments

# Convert ISO8601 YouTube duration to seconds
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

# Convert seconds into HH:MM:SS
def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

# Save all extracted YouTube data to structured files inside output directory
def save_video_data(output_dir: str, video_id: str, metadata: dict, 
                    transcript_text: str, transcript_segments: list, 
                    comments: list) -> None:
    # Create a folder specific to the video
    video_dir = os.path.join(output_dir, video_id)
    os.makedirs(video_dir, exist_ok=True)
    
    # Save metadata JSON
    if metadata:
        with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Save full transcript text
    if transcript_text:
        with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
            f.write(transcript_text)
    
    # Save detailed transcript segments
    if transcript_segments:
        with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
            json.dump(transcript_segments, f, indent=2, ensure_ascii=False)
    
    # Save comments
    if comments:
        with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2, ensure_ascii=False)
    
    # Confirmation message for saved folder
    print(f"  [SAVED] Data saved to {video_dir}")
