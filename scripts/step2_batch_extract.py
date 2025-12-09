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
    try:
        print(f"    Fetching comments from YouTube API...", end="", flush=True)
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )
            response = request.execute()
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comment_data = {
                    "author": comment.get("authorDisplayName"),
                    "text": comment.get("textDisplay"),
                    "likeCount": comment.get("likeCount"),
                    "publishedAt": comment.get("publishedAt"),
                    "replies": []
                }
                
                if "replies" in item:
                    for reply in item["replies"]["comments"]:
                        reply_snippet = reply["snippet"]
                        reply_data = {
                            "author": reply_snippet.get("authorDisplayName"),
                            "text": reply_snippet.get("textDisplay"),
                            "likeCount": reply_snippet.get("likeCount"),
                            "publishedAt": reply_snippet.get("publishedAt")
                        }
                        comment_data["replies"].append(reply_data)
                
                comments.append(comment_data)
                else:
                        try:
                            reply_request = youtube.comments().list(
                                part="snippet",
                                parentId=top_comment['id'],
                                maxResults=min(50, total_reply_count),
                                textFormat="plainText"
                            )
                            reply_response = reply_request.execute()
                            for reply_item in reply_response.get("items", []):
                                reply_snippet = reply_item["snippet"]
                                reply_data = {
                                    "author": reply_snippet.get("authorDisplayName"),
                                    "text": reply_snippet.get("textDisplay"),
                                    "likeCount": reply_snippet.get("likeCount"),
                                    "publishedAt": reply_snippet.get("publishedAt")
                                }
                                comment_data["replies"].append(reply_data)
    
def load_video_list(input_dir: str) -> list:
    # Load video URLs from CSV.
    csv_path = os.path.join(input_dir, 'video_urls.csv')

    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found!")
        sys.exit(1)
        
    videos = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            videos.append(row['video_url'])
    return videos

def main():
    parser = argparse.ArgumentParser(description='Batch extract video data')
    parser.add_argument('--skip-existing', action='store_true', help='Skip videos with existing data')
    parser.add_argument('--transcript-delay', type=int, default=3, help='Delay between transcript fetches (default: 3s)')
    
    # Load video list
    videos = load_video_list(input_dir)
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    # Stats
    stats = {
        'metadata': {'success': 0, 'failed': 0, 'skipped': 0},
        'transcript': {'success': 0, 'failed': 0, 'skipped': 0},
        'comments': {'success': 0, 'failed': 0, 'skipped': 0}
    }
    for i, video in enumerate(videos, 1):
        video_id = video['video_id']
        video_dir = os.path.join(raw_dir, video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        print(f"\n[{i}/{len(videos)}] {video_id}")
        # Metadata
        metadata_path = os.path.join(video_dir, 'metadata.json')
        if os.path.exists(metadata_path) and args.skip_existing:
            print("  Metadata exists, skipping.")
            stats['metadata']['skipped'] += 1
        else:
            metadata = get_video_metadata(youtube, video_id)
            if metadata:
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                stats['metadata']['success'] += 1
            else:
                stats['metadata']['failed'] += 1    
        
        # Transcript
        transcript_path = os.path.join(video_dir, 'transcript.json')
        if os.path.exists(transcript_path) and args.skip_existing:
            print("  Transcript exists, skipping.")
            stats['transcript']['skipped'] += 1
        else:
            transcript, transcript_data = get_transcript_supadata(video_id)
            if transcript:
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'transcript': transcript,
                        'data': transcript_data
                    }, f, indent=2, ensure_ascii=False)
                stats['transcript']['success'] += 1
            else:
                stats['transcript']['failed'] += 1      
            time.sleep(args.transcript_delay)
        # Comments
        comments_path = os.path.join(video_dir, 'comments.json')
        if os.path.exists(comments_path) and args.skip_existing:
            print("  Comments exist, skipping.")
            stats['comments']['skipped'] += 1
        else:   
            comments = get_comments_with_replies(youtube, video_id, max_comments=MAX_COMMENTS_PER_VIDEO)
            if comments:
                with open(comments_path, 'w', encoding='utf-8') as f:
                    json.dump(comments, f, indent=2, ensure_ascii=False)
                stats['comments']['success'] += 1
            else:
                stats['comments']['failed'] += 1

if __name__ == "__main__":
    main()
