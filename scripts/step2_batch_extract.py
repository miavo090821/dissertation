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

from googleapiclient.discovery import build


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from URL or return as-is."""
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
    """Fetch video metadata using YouTube Data API."""
    try:
        print(f"    Fetching metadata from YouTube API...", end="", flush=True)
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=video_id
        )
        response = request.execute()
        print(" done", flush=True)
        
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
    except Exception as e:
        print(f"    Metadata error: {e}")
    return None


def get_transcript_supadata(video_id: str) -> tuple:
    """Fetch transcript using Supadata API."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        print(f"    Fetching transcript from Supadata...", end="", flush=True)
        response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=15)
        print(" done", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            
            if content:
                # Get timestamped segments
                params["text"] = "false"
                seg_response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)
                
                segments = []
                if seg_response.status_code == 200:
                    seg_data = seg_response.json()
                    raw_segments = seg_data.get("content", [])
                    if isinstance(raw_segments, list):
                        for seg in raw_segments:
                            segments.append({
                                "text": seg.get("text", ""),
                                "start": seg.get("offset", 0) / 1000,
                                "duration": seg.get("duration", 0) / 1000
                            })
    except Exception as e:
        print(f"    Transcript error: {e}")
    
    return None, None


def get_comments_with_replies(youtube, video_id: str, max_comments: int = 200) -> list:
    """Fetch comments with replies using YouTube Data API."""
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
            
            for item in response.get('items', []):
                top_comment = item['snippet']['topLevelComment']
                snippet = top_comment['snippet']
                total_reply_count = item['snippet'].get('totalReplyCount', 0)
                
                comment_data = {
                    'id': top_comment['id'],
                    'author': snippet.get('authorDisplayName', ''),
                    'author_channel_id': snippet.get('authorChannelId', {}).get('value', ''),
                    'text': snippet.get('textDisplay', ''),
                    'like_count': snippet.get('likeCount', 0),
                    'published_at': snippet.get('publishedAt', ''),
                    'is_reply': False,
                    'reply_count': total_reply_count,
                    'replies': []
                }
                
                if total_reply_count > 0:
                    included_replies = item.get('replies', {}).get('comments', [])
                    
                    if total_reply_count <= len(included_replies):
                        for reply in included_replies:
                            reply_snippet = reply['snippet']
                            comment_data['replies'].append({
                                'id': reply['id'],
                                'author': reply_snippet.get('authorDisplayName', ''),
                                'text': reply_snippet.get('textDisplay', ''),
                                'like_count': reply_snippet.get('likeCount', 0),
                                'published_at': reply_snippet.get('publishedAt', ''),
                                'is_reply': True
                            })
                    else:
                        try:
                            reply_request = youtube.comments().list(
                                part="snippet",
                                parentId=top_comment['id'],
                                maxResults=min(50, total_reply_count),
                                textFormat="plainText"
                            )
                            reply_response = reply_request.execute()
                            
                            for reply in reply_response.get('items', []):
                                reply_snippet = reply['snippet']
                                comment_data['replies'].append({
                                    'id': reply['id'],
                                    'author': reply_snippet.get('authorDisplayName', ''),
                                    'text': reply_snippet.get('textDisplay', ''),
                                    'like_count': reply_snippet.get('likeCount', 0),
                                    'published_at': reply_snippet.get('publishedAt', ''),
                                    'is_reply': True
                                })
                            time.sleep(0.1)
                        except Exception:
                            pass
                
                comments.append(comment_data)
                
                if len(comments) >= max_comments:
                    break
                
    except Exception as e:
        if "commentsDisabled" not in str(e):
            print(f"    Comments error: {e}", flush=True)
        else:
            print(" (disabled)", flush=True)
    
    return comments


def load_video_list(input_dir: str) -> list:
    """Load video URLs from CSV."""
    csv_path = os.path.join(input_dir, 'video_urls.csv')
    
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found!")
        sys.exit(1)
    
    videos = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try multiple possible column names (handles BOM and variations)
            url = None
            # Check all possible URL column names
            for key in row.keys():
                key_clean = key.strip().lstrip('\ufeff').lower()
                if key_clean == 'url':
                    url = row[key]
                    break
            
            # Fallback to direct key access
            if not url:
                url = row.get('url') or row.get('URL') or row.get('video_url')
            
            # Also check if any key contains 'url' (case insensitive)
            if not url:
                for key in row.keys():
                    if 'url' in key.lower():
                        url = row[key]
                        break
            
            if url and url.strip():
                video_id = extract_video_id(url)
                videos.append({
                    'video_id': video_id,
                    'url': url,
                    **{k: v for k, v in row.items() if k not in ['url', 'URL', 'video_url', '\ufeffurl'] and not k.startswith('\ufeff')}
                })
    
    return videos


def main():
    parser = argparse.ArgumentParser(description='Batch extract video data')
    parser.add_argument('--skip-existing', action='store_true', help='Skip videos with existing data')
    parser.add_argument('--transcript-delay', type=int, default=3, help='Delay between transcript fetches (default: 3s)')
    parser.add_argument('--max-comments', type=int, default=200, help='Max comments per video (default: 200)')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    input_dir = os.path.join(base_dir, DATA_INPUT_DIR)
    
    # Load video list
    videos = load_video_list(input_dir)
    
    if not videos:
        print("ERROR: No videos found in video_urls.csv")
        sys.exit(1)
    
    print("STEP 2: BATCH EXTRACT ALL VIDEOS")
    print(f"Videos: {len(videos)} | Delay: {args.transcript_delay}s | Max comments: {args.max_comments}")
    print(f"Skip existing: {args.skip_existing}\n")
    
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
        
        # Check existing files
        has_metadata = os.path.exists(os.path.join(video_dir, 'metadata.json'))
        has_transcript = os.path.exists(os.path.join(video_dir, 'transcript.txt'))
        has_comments = os.path.exists(os.path.join(video_dir, 'comments.json'))
        
        if args.skip_existing and has_metadata:
            print("  [Metadata] Skipped")
            stats['metadata']['skipped'] += 1
        else:
            metadata = get_video_metadata(youtube, video_id)
            if metadata:
                metadata.update({k: v for k, v in video.items() if k not in ['video_id', 'url']})
                with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                print(f"  [Metadata] {metadata['title'][:40]}...")
                print("  SUCCESS: Metadata saved")
                stats['metadata']['success'] += 1
            else:
                print("  [Metadata] ERROR: Failed")
                stats['metadata']['failed'] += 1
        
        if args.skip_existing and has_transcript:
            print("  [Transcript] Skipped")
            stats['transcript']['skipped'] += 1
        else:
            transcript_text, segments = get_transcript_supadata(video_id)
            if transcript_text:
                with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                if segments:
                    with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
                        json.dump(segments, f, indent=2, ensure_ascii=False)
                print(f"  [Transcript] {len(transcript_text.split()):,} words")
                print("  SUCCESS: Transcript saved")
                stats['transcript']['success'] += 1
            else:
                print("  [Transcript] WARNING: Not available")
                stats['transcript']['failed'] += 1
            
            if i < len(videos):
                time.sleep(args.transcript_delay)
        
        if args.skip_existing and has_comments:
            print("  [Comments] Skipped")
            stats['comments']['skipped'] += 1
        else:
            comments = get_comments_with_replies(youtube, video_id, max_comments=args.max_comments)
            if comments:
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump(comments, f, indent=2, ensure_ascii=False)
                total_replies = sum(len(c.get('replies', [])) for c in comments)
                print(f"  [Comments] {len(comments)} comments, {total_replies} replies")
                print("  SUCCESS: Comments saved")
                stats['comments']['success'] += 1
            else:
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print("  [Comments] WARNING: None available")
                stats['comments']['failed'] += 1
        
        time.sleep(0.5)
    
    print("\nCOMPLETE")
    print(f"{'Component':<15} {'Success':>10} {'Failed':>10} {'Skipped':>10}")
    print("-" * 45)
    for component, counts in stats.items():
        print(f"{component.capitalize():<15} {counts['success']:>10} {counts['failed']:>10} {counts['skipped']:>10}")
    
    print(f"\nOutput: {raw_dir}")
    print("Next: Run step3_sensitivity_analysis.py")


if __name__ == "__main__":
    main()