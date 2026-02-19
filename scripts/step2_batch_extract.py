# Step 2: Batch Extract All Videos
# Process all videos from video_urls.csv using YouTube Data API v3 and Supadata API
# Extract metadata, transcripts and comments with replies for all videos

import sys
import os
import json
import re
import csv
import time
import argparse
import requests

# Ensure the parent directory of the scripts folder is on the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Compute project base directory from this file location
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add base directory to sys.path so config and other modules can be imported
sys.path.insert(0, base_dir)

try:
    # Import configuration values and constants
    from config import (
        YOUTUBE_API_KEY,
        DATA_RAW_DIR,
        DATA_INPUT_DIR,
        MAX_COMMENTS_PER_VIDEO,
        SUPADATA_API_KEY,
        SUPADATA_BASE_URL
    )
except ImportError as e:
    # Handle missing config file
    print(f"ERROR: Could not import config.py")
    print(f"Expected location: {os.path.join(base_dir, 'config.py')}")
    print(f"Make sure you're running from the dissertation directory")
    sys.exit(1)
except SystemExit:
    # Allow explicit system exit to propagate
    raise
except Exception as e:
    # Handle other errors while loading config
    print(f"ERROR: config.py found but failed to load: {e}")
    sys.exit(1)

# Import YouTube Data API client
from googleapiclient.discovery import build


def extract_video_id(url_or_id: str) -> str:
    # Extract a YouTube video id from a full url or return it unchanged if it already looks like an id
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    # Check the input against each pattern
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            # Return the first captured group which is the video id
            return match.group(1)
    # Fallback to returning the input as is
    return url_or_id


def get_video_metadata(youtube, video_id: str) -> dict:
    # Fetch video metadata from the YouTube Data API
    try:
        # Build request to retrieve snippet statistics content details and status
        print(f"    Fetching metadata from YouTube API...", end="", flush=True)
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=video_id
        )
        # Execute the request
        response = request.execute()
        print(" done", flush=True)
        
        # Ensure at least one item is returned
        if response['items']:
            item = response['items'][0]
            # Access snippet block with basic details
            snippet = item['snippet']
            # Access statistics block
            stats = item['statistics']
            # Access content details such as duration
            content = item['contentDetails']
            
            # Build a simplified metadata dictionary
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
        # Log any metadata fetch error
        print(f"    Metadata error: {e}")
    # Return None if something went wrong
    return None


def get_transcript_supadata(video_id: str) -> tuple:
    # Fetch transcript for a video using Supadata API and return plain text and segments
    # Build the watch url that Supadata expects
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Initial request parameters asking for plain text transcript
    params = {
        "url": url,
        "lang": "en",
        "text": "true",
        "mode": "native"
    }
    
    # Supadata authentication header
    headers = {"x-api-key": SUPADATA_API_KEY}
    
    try:
        # Request full transcript text
        print(f"    Fetching transcript from Supadata...", end="", flush=True)
        response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=15)
        print(" done", flush=True)
        
        # Successful response with transcript content
        if response.status_code == 200:
            data = response.json()
            # Get plain text transcript content
            content = data.get("content", "")
            
            if content:
                # Request timestamped segments by toggling text flag
                params["text"] = "false"
                seg_response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)
                
                segments = []
                # If the segments request is successful attempt to parse segment list
                if seg_response.status_code == 200:
                    seg_data = seg_response.json()
                    raw_segments = seg_data.get("content", [])
                    # Ensure the content field contains a list of segments
                    if isinstance(raw_segments, list):
                        for seg in raw_segments:
                            # Convert offset and duration from milliseconds to seconds
                            segments.append({
                                "text": seg.get("text", ""),
                                "start": seg.get("offset", 0) / 1000,
                                "duration": seg.get("duration", 0) / 1000
                            })
                # Return both text and segments
                return content, segments
        # If rate limited wait briefly and retry once
        elif response.status_code == 429:
            print("    Rate limited waiting 10 seconds")
            time.sleep(10)
            return get_transcript_supadata(video_id)
            
    except Exception as e:
        # Log any error that occurs during transcript fetch
        print(f"    Transcript error: {e}")
    
    # Return placeholders if transcript is not available
    return None, None


def get_comments_with_replies(youtube, video_id: str, max_comments: int = 200) -> list:
    # Fetch top level comments and their replies using YouTube Data API
    comments = []
    # Pagination token for comment threads
    next_page_token = None
    
    try:
        print(f"    Fetching comments from YouTube API...", end="", flush=True)
        # Continue fetching until we hit the limit or there are no more comments
        while len(comments) < max_comments:
            # Build commentThreads request to fetch top level comments and possible replies block
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )
            # Execute the request
            response = request.execute()
            
            # Iterate through each comment thread item
            for item in response.get('items', []):
                # Extract the top level comment object
                top_comment = item['snippet']['topLevelComment']
                snippet = top_comment['snippet']
                # Total reply count for this comment
                total_reply_count = item['snippet'].get('totalReplyCount', 0)
                
                # Build base data structure for the top level comment
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
                
                # If this comment has replies attempt to collect them
                if total_reply_count > 0:
                    # Replies may already be included in the thread object
                    included_replies = item.get('replies', {}).get('comments', [])
                    
                    # If all replies are present in included_replies use them directly
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
                        # Otherwise make a separate request to the comments endpoint for more replies
                        try:
                            reply_request = youtube.comments().list(
                                part="snippet",
                                parentId=top_comment['id'],
                                maxResults=min(50, total_reply_count),
                                textFormat="plainText"
                            )
                            reply_response = reply_request.execute()
                            
                            # Collect replies into the nested list
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
                            # Short pause between reply fetches to be polite with the API
                            time.sleep(0.1)
                        except Exception:
                            # Ignore secondary reply fetch errors to avoid breaking the whole run
                            pass
                
                # Add this comment thread to the result list
                comments.append(comment_data)
                
                # Stop if we have reached the desired maximum number of comments
                if len(comments) >= max_comments:
                    break
            
            # Update pagination token
            next_page_token = response.get('nextPageToken')
            # If there is no token we have reached the last page
            if not next_page_token:
                break
        # Print out how many comments we managed to collect
        print(f" ({len(comments)} comments)", flush=True)
                
    except Exception as e:
        # If comments are not disabled report the error
        if "commentsDisabled" not in str(e):
            print(f"    Comments error: {e}", flush=True)
        else:
            # If comments are disabled note that in the output
            print(" (disabled)", flush=True)
    
    # Return the list of collected comments and replies
    return comments


def load_video_list(input_dir: str) -> list:
    # Load video urls and any extra metadata from video_urls.csv
    csv_path = os.path.join(input_dir, 'video_urls.csv')
    
    # Stop early if the csv is missing
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found!")
        sys.exit(1)
    
    videos = []
    # Open csv file with support for possible byte order mark
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Iterate through each row of the csv
        for row in reader:
            # Initialise url as None until we find a suitable column
            url = None
            # Try multiple possible column names and clean any stray characters
            for key in row.keys():
                key_clean = key.strip().lstrip('\ufeff').lower()
                if key_clean == 'url':
                    url = row[key]
                    break
            
            # Fallback to common url field names if not found above
            if not url:
                url = row.get('url') or row.get('URL') or row.get('video_url')
            
            # As a final attempt check any column whose name contains the word url
            if not url:
                for key in row.keys():
                    if 'url' in key.lower():
                        url = row[key]
                        break
            
            # Only process rows that have a non empty url
            if url and url.strip():
                # Normalise the url into a video id
                video_id = extract_video_id(url)
                # Add video information and any other fields from the csv row
                videos.append({
                    'video_id': video_id,
                    'url': url,
                    **{
                        k: v
                        for k, v in row.items()
                        if k not in ['url', 'URL', 'video_url', '\ufeffurl'] and not k.startswith('\ufeff')
                    }
                })
    
    # Return list of video entries with ids and urls
    return videos


def main():
    # Create command line argument parser for batch extraction options
    parser = argparse.ArgumentParser(description='Batch extract video data')
    # Option to skip videos that already have output files
    parser.add_argument('--skip-existing', action='store_true', help='Skip videos with existing data')
    # Option to control delay between transcript fetch requests
    parser.add_argument('--transcript-delay', type=int, default=3, help='Delay between transcript fetches (default: 3s)')
    # Option to control maximum number of comments per video
    parser.add_argument('--max-comments', type=int, default=200, help='Max comments per video (default: 200)')
    # Parse command line arguments
    args = parser.parse_args()
    
    # Compute base directory from this file again in case script is moved
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Directory where raw per video folders will be stored
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    # Directory where input csv files are stored
    input_dir = os.path.join(base_dir, DATA_INPUT_DIR)
    
    # Load list of videos to process from csv
    videos = load_video_list(input_dir)
    
    # If no videos are present abort early
    if not videos:
        print("ERROR: No videos found in video_urls.csv")
        sys.exit(1)
    
    # Print summary of the batch job configuration
    print("STEP 2: BATCH EXTRACT ALL VIDEOS")
    print(f"Videos: {len(videos)} | Delay: {args.transcript_delay}s | Max comments: {args.max_comments}")
    print(f"Skip existing: {args.skip_existing}\n")
    
    # Create a YouTube API client using the developer key from config
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    # Prepare statistics counters for each component stage
    stats = {
        'metadata': {'success': 0, 'failed': 0, 'skipped': 0},
        'transcript': {'success': 0, 'failed': 0, 'skipped': 0},
        'comments': {'success': 0, 'failed': 0, 'skipped': 0}
    }
    
    # Iterate through all videos from the input list with index
    for i, video in enumerate(videos, 1):
        video_id = video['video_id']
        # Create directory for this specific video id
        video_dir = os.path.join(raw_dir, video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        # Progress header for this video
        print(f"\n[{i}/{len(videos)}] {video_id}")
        
        # Check whether each component file already exists
        has_metadata = os.path.exists(os.path.join(video_dir, 'metadata.json'))
        has_transcript = os.path.exists(os.path.join(video_dir, 'transcript.txt'))
        has_comments = os.path.exists(os.path.join(video_dir, 'comments.json'))
        
        # Handle metadata stage
        if args.skip_existing and has_metadata:
            # Respect skip flag and record that metadata was skipped
            print("  [Metadata] Skipped")
            stats['metadata']['skipped'] += 1
        else:
            # Fetch metadata for this video
            metadata = get_video_metadata(youtube, video_id)
            if metadata:
                # Merge any extra columns from the csv row into the metadata
                metadata.update({k: v for k, v in video.items() if k not in ['video_id', 'url']})
                # Save metadata as json file in the video folder
                with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                # Print truncated title for quick inspection
                print(f"  [Metadata] {metadata['title'][:40]}...")
                print("  SUCCESS: Metadata saved")
                stats['metadata']['success'] += 1
            else:
                # Record failure if metadata fetch did not succeed
                print("  [Metadata] ERROR: Failed")
                stats['metadata']['failed'] += 1
        
        # Handle transcript stage
        if args.skip_existing and has_transcript:
            # Skip transcript if already present and skip flag is set
            print("  [Transcript] Skipped")
            stats['transcript']['skipped'] += 1
        else:
            # Fetch transcript text and segments from Supadata
            transcript_text, segments = get_transcript_supadata(video_id)
            if transcript_text:
                # Save plain text transcript
                with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                # Save segments with time codes if available
                if segments:
                    with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
                        json.dump(segments, f, indent=2, ensure_ascii=False)
                # Print word count for sanity check
                print(f"  [Transcript] {len(transcript_text.split()):,} words")
                print("  SUCCESS: Transcript saved")
                stats['transcript']['success'] += 1
            else:
                # Log warning when transcript is not available
                print("  [Transcript] WARNING: Not available")
                stats['transcript']['failed'] += 1
            
            # Respect delay between transcript calls to avoid stressing the service
            if i < len(videos):
                time.sleep(args.transcript_delay)
        
        # Handle comments stage
        if args.skip_existing and has_comments:
            # Skip if comments already present and skip flag is set
            print("  [Comments] Skipped")
            stats['comments']['skipped'] += 1
        else:
            # Fetch comments and replies for this video
            comments = get_comments_with_replies(youtube, video_id, max_comments=args.max_comments)
            if comments:
                # Save comments to json file
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump(comments, f, indent=2, ensure_ascii=False)
                # Count total replies for reporting
                total_replies = sum(len(c.get('replies', [])) for c in comments)
                print(f"  [Comments] {len(comments)} comments, {total_replies} replies")
                print("  SUCCESS: Comments saved")
                stats['comments']['success'] += 1
            else:
                # If no comments write an empty list file so downstream code can still read it
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print("  [Comments] WARNING: None available")
                stats['comments']['failed'] += 1
        
        # Small pause between videos to be gentle with the APIs
        time.sleep(0.5)
    
    # Print final summary of batch extraction results
    print("\nCOMPLETE")
    print(f"{'Component':<15} {'Success':>10} {'Failed':>10} {'Skipped':>10}")
    print("-" * 45)
    for component, counts in stats.items():
        print(f"{component.capitalize():<15} {counts['success']:>10} {counts['failed']:>10} {counts['skipped']:>10}")
    
    # Show where all raw data has been saved
    print(f"\nOutput: {raw_dir}")
    print("Next: Run step3_sensitivity_analysis.py")

if __name__ == "__main__":
    # Entry point when script is executed directly
    main()
