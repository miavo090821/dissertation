# Step 1: Extract Single Video
# Test extraction for ONE video using YouTube Data API v3
# and Supadata API.
# Extracts metadata, transcript, and comments with replies.

import sys
import os
import json
import re
import time
import requests

# Determine the project base directory (one level above /scripts)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add project root to sys.path to allow importing config.py
sys.path.insert(0, base_dir)

try:
    # Import API keys + directory settings
    from config import YOUTUBE_API_KEY, DATA_RAW_DIR, SUPADATA_API_KEY, SUPADATA_BASE_URL
except ImportError as e:
    # Config file not found; script cannot run
    print(f"ERROR: Could not import config.py")
    print(f"Expected location: {os.path.join(base_dir, 'config.py')}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Import error: {e}")
    print("\nMake sure you're running from the dissertation directory:")
    print("  cd dissertation")
    print("  python scripts/step1_extract_single_video.py \"VIDEO_URL\"")
    sys.exit(1)
except SystemExit:
    raise
except Exception as e:
    # Config exists but has errors
    print(f"ERROR: config.py found but failed to load: {e}")
    sys.exit(1)

# Google API client to interact with YouTube Data API
from googleapiclient.discovery import build


def extract_video_id(url_or_id: str) -> str:
    # Extracts a YouTube video ID from any common URL pattern
    # Falls back to returning the input unchanged if no match
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
    # Fetches metadata fields: title, description, stats, duration, etc.
    try:
        # Build API request for video metadata
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=video_id
        )
        response = request.execute()

        # Ensure at least one result returned
        if response['items']:
            item = response['items'][0]
            snippet = item['snippet']
            stats = item['statistics']
            content = item['contentDetails']

            # Return a clean dictionary of metadata fields
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
        print(f"  Error fetching metadata: {e}")

    return None


def get_transcript_supadata(video_id: str):
    # Fetches full transcript text + segment-level timestamps via Supadata API
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    # Initial request for full text transcript
    params = {
        "url": youtube_url,
        "lang": "en",
        "text": "true",
        "mode": "native"
    }
    headers = {"x-api-key": SUPADATA_API_KEY}

    try:
        response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)

        # 200 → transcript returned
        if response.status_code == 200:
            data = response.json()
            full_text = data.get("content", "")

            if full_text:
                # Make a second call for segments (offset + duration)
                params["text"] = "false"
                seg_response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)

                segments = []
                if seg_response.status_code == 200:
                    seg_data = seg_response.json()
                    raw_segments = seg_data.get("content", [])

                    # Convert timestamps to seconds
                    for seg in raw_segments:
                        segments.append({
                            "text": seg.get("text", ""),
                            "start": seg.get("offset", 0) / 1000,
                            "duration": seg.get("duration", 0) / 1000
                        })

                return full_text, segments

        elif response.status_code == 206:
            # 206 = No transcript available
            print("  No transcript available")

        else:
            print(f"  Transcript error: HTTP {response.status_code}")

    except Exception as e:
        print(f"  Error fetching transcript: {e}")

    return None, None


def get_comments_with_replies(youtube, video_id: str, max_comments: int = 100) -> list:
    # Fetches top-level comments and replies (up to max_comments)
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_comments:
            # Request comment threads
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
                reply_count = item['snippet'].get('totalReplyCount', 0)

                # Structure for this comment
                comment_data = {
                    'id': top_comment['id'],
                    'author': snippet.get('authorDisplayName', ''),
                    'author_channel_id': snippet.get('authorChannelId', {}).get('value', ''),
                    'text': snippet.get('textDisplay', ''),
                    'like_count': snippet.get('likeCount', 0),
                    'published_at': snippet.get('publishedAt', ''),
                    'is_reply': False,
                    'reply_count': reply_count,
                    'replies': []
                }

                # If this comment has replies
                if reply_count > 0:
                    included_replies = item.get('replies', {}).get('comments', [])

                    # If YouTube already included all replies
                    if reply_count <= len(included_replies):
                        for reply in included_replies:
                            rs = reply['snippet']
                            comment_data['replies'].append({
                                'id': reply['id'],
                                'author': rs.get('authorDisplayName', ''),
                                'text': rs.get('textDisplay', ''),
                                'like_count': rs.get('likeCount', 0),
                                'published_at': rs.get('publishedAt', ''),
                                'is_reply': True
                            })
                    else:
                        # Extra request needed for more replies
                        reply_req = youtube.comments().list(
                            part="snippet",
                            parentId=top_comment['id'],
                            maxResults=min(50, reply_count),
                            textFormat="plainText"
                        )
                        reply_res = reply_req.execute()

                        for reply in reply_res.get('items', []):
                            rs = reply['snippet']
                            comment_data['replies'].append({
                                'id': reply['id'],
                                'author': rs.get('authorDisplayName', ''),
                                'text': rs.get('textDisplay', ''),
                                'like_count': rs.get('likeCount', 0),
                                'published_at': rs.get('publishedAt', ''),
                                'is_reply': True
                            })

                comments.append(comment_data)

                if len(comments) >= max_comments:
                    break

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

    except Exception as e:
        if "commentsDisabled" in str(e):
            print("  Comments disabled for this video")
        else:
            print(f"  Error fetching comments: {e}")

    return comments


def main():
    # Ensure the video ID or URL is provided
    if len(sys.argv) < 2:
        print("Usage: python step1_extract_single_video.py VIDEO_URL_OR_ID")
        sys.exit(1)

    # Take first argument after script name
    video_input = sys.argv[1]

    # Convert URL → video ID if needed
    video_id = extract_video_id(video_input)

    print("STEP 1: EXTRACT SINGLE VIDEO")
    print(f"Video ID: {video_id}\n")

    # Create YouTube Data API client
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # Create output directory for this video's files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_dir = os.path.join(base_dir, DATA_RAW_DIR, video_id)
    os.makedirs(video_dir, exist_ok=True)

    # 1. METADATA
    print("[1/3] Fetching metadata...")
    metadata = get_video_metadata(youtube, video_id)

    if metadata:
        with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"  Title: {metadata['title'][:50]}...")
        print(f"  Views: {metadata['view_count']:,}, Comments: {metadata['comment_count']:,}")
        print("  SUCCESS: Metadata saved to metadata.json")
    else:
        print("  ERROR: Failed to fetch metadata")
        sys.exit(1)

    # 2. TRANSCRIPT

    print("\n[2/3] Fetching transcript...")
    transcript_text, segments = get_transcript_supadata(video_id)

    if transcript_text:
        # Save full transcript
        with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
            f.write(transcript_text)

        # Save segment-level transcript if available
        if segments:
            with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)

        print(f"  Words: {len(transcript_text.split()):,}")
        print("  SUCCESS: Transcript saved to transcript.txt")
    else:
        print("  WARNING: No transcript available")

    # 3. COMMENTS
    print("\n[3/3] Fetching comments...")
    comments = get_comments_with_replies(youtube, video_id)

    if comments:
        with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2, ensure_ascii=False)

        total_replies = sum(len(c['replies']) for c in comments)
        print(f"  Comments: {len(comments)}, Replies: {total_replies}")
        print("  SUCCESS: Comments saved to comments.json")
    else:
        print("  WARNING: No comments available")

    print("\nCOMPLETE: All files saved to", video_dir)
    print("Next: Run step2_batch_extract.py for multiple videos")

if __name__ == "__main__":
    main()