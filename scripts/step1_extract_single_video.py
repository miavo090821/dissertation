# Step 1: Extract Single Video
# Test extraction for ONE video using YouTube Data API v3
# and Supadata API.
# Extracts metadata, transcript, and comments with replies.

import sys
import os
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

def extract_video_id(url_or_id: str) -> str:
    # Extract video ID from URL or return as-is if already an ID
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

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
    
    def get_comments_with_replies(youtube, video_id: str, max_comments: int = 100) -> list:
    # Fetch comments with replies using YouTube Data API.
    comments = []
    next_page_token = None
    
    try:
        while len(comments) < max_comments:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText"
            ).execute()
            
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
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
    except Exception as e:
        print(f"Error fetching comments: {e}")
    return comments


def main():
    if len(sys.argv) < 2:
        print("Usage: python step1_extract_single_video.py VIDEO_URL_OR_ID")
        sys.exit(1)
    
    video_input = sys.argv[1]
    video_id = extract_video_id(video_input)
    
    print("STEP 1: EXTRACT SINGLE VIDEO")
    print(f"Video ID: {video_id}\n")
    
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_dir = os.path.join(base_dir, DATA_RAW_DIR, video_id)
    os.makedirs(video_dir, exist_ok=True) 
    
    print("[1/3] Fetching metadata...")
    metadata = get_video_metadata(youtube, video_id)
    
    print("\n[2/3] Fetching transcript...")
    transcript_text, segments = get_transcript_supadata(video_id)

    print("\n[3/3] Fetching comments...")
    comments = get_comments_with_replies(youtube, video_id, max_comments=100)


if __name__ == "__main__":
    main()
