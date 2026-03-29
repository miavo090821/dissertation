# youtube api helpers
#
#1. wraps the youtube data api v3 and youtube-transcript-api for our data collection
#2. handles video metadata, channel stats, transcripts, and comments all in one place
#3. transcript fetching has retry logic with exponential backoff for rate limiting
#4. saves everything into per-video folders as json/txt files

# re is Python's built-in regular expression library
# I use it to search text patterns, for example:
# - extracting the 11-character YouTube video ID from different URL formats
# - parsing ISO 8601 duration strings such as "PT1H2M3S"
import re

# json is Python's built-in library for reading and writing JSON data
# i use it to save structured output such as metadata, transcript segments,
# and comments into .json files
import json

# os is Python's built-in operating system library
# i use it for working with file paths and folders, for example:
# - joining folder and file names safely with os.path.join()
# - creating directories with os.makedirs()
import os

# datetime is from Python's built-in datetime module
# i use datetime.now().isoformat() to record when data was collected
# This is useful for transparency and reproducibility in the research pipeline
from datetime import datetime

# googleapiclient.discovery.build is part of the google-api-python-client library
# (a third-party library, not built into Python)
# i use it to create a YouTube API client that can send requests to
# YouTube Data API v3
from googleapiclient.discovery import build

# YouTubeTranscriptApi is from the youtube-transcript-api package
# (a third-party library)
# i use it to fetch video transcripts/subtitles without having to scrape
# them manually from the webpage
from youtube_transcript_api import YouTubeTranscriptApi


# extracts the 11-char video id from any youtube url format
def get_video_id(url: str) -> str:
    """parses watch urls, youtu.be shortlinks, embeds, and raw ids."""
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]

    # Why this is needed:
    # - The YouTube API works with video IDs, not full URLs.
    # - Users may provide links in different formats, such as:
    #     https://www.youtube.com/watch?v=ABCDEFGHIJK
    #     https://youtu.be/ABCDEFGHIJK
    #     https://www.youtube.com/embed/ABCDEFGHIJK
    #     ABCDEFGHIJK

    # Returns:
    #     The 11-character YouTube video ID as a string.

# Try each pattern one by one until one matches.
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # group(1) is the part inside the brackets (...) in the regex,
            # which is the actual video ID we want.
            return match.group(1)

    raise ValueError(f"Could not extract video ID from: {url}")   
    # If nothing matched, raise an error so the caller knows the input was invalid.
 

# creates a youtube api client from the api key
def get_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)

    # # Why this is helpful:
    # - We need a client object before making API requests.
    # - Keeping this in one helper function avoids repeating the same code
    #   in every metadata/comments/channel function.



# pulls title, view count, tags, etc from the youtube api for one video
def get_video_metadata(api_key: str, video_id: str) -> dict:

    # Retrieve metadata for a single YouTube video.

    # This includes:
    # - title
    # - channel name and channel ID
    # - description
    # - published date
    # - duration
    # - view/like/comment counts
    # - tags
    # - category ID

    # Returns:
    #     a dictionary of metadata if successful, otherwise None.

    try:
        # Build the YouTube client first.
        youtube = get_youtube_client(api_key)

        # Request video details from the API.
        # part=
        # - snippet: basic descriptive info like title, description, tags
        # - statistics: view/like/comment counts
        # - contentDetails: duration and some technical info

        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
             # if no items are returned, the video ID may be invalid, deleted,
        # or unavailable via the API
            print(f"  [WARNING] No video found for ID: {video_id}")
            return None

#  # The API returns a list of items, but here we only asked for one video ID,
        # so we take the first item.
        item = response['items'][0]
        snippet = item['snippet']
        stats = item['statistics']
        content = item['contentDetails']

        return { # return the relevant fields in a clean Python dictionary
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
             
              # Record when this metadata was extracted for research traceability
            
            'extracted_at': datetime.now().isoformat()
        }

    except Exception as e:
         # if anything goes wrong, print the error and return None
        # rather than crashing the whole pipeline.
        print(f"  [ERROR] Failed to fetch metadata for {video_id}: {e}")
        return None

# gets subscriber count, total views, video count for a channel
def get_channel_info(api_key: str, channel_id: str) -> dict:

"""
    Retrieve basic information about a YouTube channel.

    This includes:
    - subscriber count
    - total number of videos on the channel
    - total channel view count

    Returns:
        A dictionary if successful, otherwise None.
    """

    try:
        youtube = get_youtube_client(api_key)

 # ask the channels endpoint for statistics and snippet data
     
        request = youtube.channels().list(
            part="statistics,snippet",
            id=channel_id
        )
        response = request.execute()

        if not response.get('items'):   # If no channel is found, return None
            return None

        item = response['items'][0]
        stats = item['statistics']

        return {
            'channel_id': channel_id,
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'view_count': int(stats.get('viewCount', 0))
        }

    except Exception as e:
        print(f"  [ERROR] Failed to fetch channel info: {e}")
        return None

# fetches the transcript with retries - tries direct fetch, then autogenerated, then manual, then any language
def get_video_transcript(video_id: str, max_retries: int = 3) -> tuple:
    """grabs the english transcript for a video. has exponential backoff for
    rate limits and falls back through several methods if the first one fails."""
    import time
"""
    Retrieve a transcript for a YouTube video.

    Strategy:
    1. Try a direct transcript fetch in English first.
    2. If that fails, list all available transcripts and try:
       - generated English transcript
       - manually created English transcript
       - any available transcript as a last resort
    3. If YouTube rate-limits the request, retry using exponential backoff.

    Why exponential backoff?
    - If a server is rate-limiting us, immediately retrying often fails again.
    - Waiting longer after each failed attempt is a more polite and robust strategy.

    Returns:
        (full_text, processed_segments)
        - full_text: one joined transcript string
        - processed_segments: list of segment dictionaries with start/duration/text

    If transcript retrieval fails completely:
        (None, None)
    """
    segments = None
    last_error = None
# Retry the whole process up to max_retries times
    for attempt in range(max_retries):
        # On retries after the first attempt, wait before trying again
        if attempt > 0:
            # this is exponential backoff:
            # retry 2 waits 5s, retry 3 waits 10s, retry 4 would wait 20s, etc.
            wait_time = 5 * (2 ** (attempt - 1))
            print(f"  [RETRY] Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)

        # first attempt: direct transcript fetch 
        try:
            segments = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB']
            )
            break  # stop retry loop if successful

        except Exception as e:
            last_error = e

            # if rate-limited, go straight to the next retry attempt.
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue

        # second attempt: inspect available transcript options 
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try generated English transcript first.
            try:
                transcript = transcript_list.find_generated_transcript(
                    ['en', 'en-US', 'en-GB']
                )
                segments = transcript.fetch()
                break
            except Exception:
                pass

            # if that fails, try a manually created English transcript
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    ['en', 'en-US', 'en-GB']
                )
                segments = transcript.fetch()
                break
            except Exception:
                pass

            # final fallback: just use the first available transcript,
            # even if it is not English
            available = list(transcript_list)
            if available:
                segments = available[0].fetch()
                break

        except Exception as e:
            last_error = e
            if '429' in str(e) or 'Too Many Requests' in str(e):
                continue

    # if no transcript was found after all attempts, return None values
    if not segments:
        error_msg = str(last_error) if last_error else "Unknown error"

        if '429' in error_msg or 'Too Many Requests' in error_msg:
            print(f"  [WARNING] Rate limited by YouTube for {video_id}. Try again later.")
        else:
            print(f"  [WARNING] Could not retrieve transcript for {video_id}: {error_msg[:100]}")

        return None, None

    # Convert transcript segments into cleaner output
    # We build:
    # 1. one full transcript string
    # 2. one list of processed segment dictionaries
    full_text_parts = []
    processed_segments = []

    for seg in segments:
        try:
            # some transcript libraries return dictionaries,
            # others may return objects. This code supports both.
            start = seg['start'] if isinstance(seg, dict) else seg.start
            duration = seg['duration'] if isinstance(seg, dict) else seg.duration
            text = seg['text'] if isinstance(seg, dict) else seg.text
        except (KeyError, AttributeError):
            # skip malformed segment entries rather than crashing.
            continue

        full_text_parts.append(text)
        processed_segments.append({
            'start': start,
            'duration': duration,
            'text': text
        })

    # join all transcript pieces into one full transcript string
    full_text = ' '.join(full_text_parts)

    return full_text, processed_segments

# fetches top comments using pagination, up to max_comments
def get_video_comments(api_key: str, video_id: str, max_comments: int = 200) -> list:
    """pulls comments sorted by relevance. handles disabled comments gracefully."""
    youtube = get_youtube_client(api_key)
    comments = []
    next_page_token = None

    # Notes:
    # - Comments are fetched in pages
    # - The API can return at most 100 per request, so we use pagination
    # - We sort by relevance rather than date in this version
    # - If comments are disabled, the function handles that gracefully

    # Returns:
    #     a list of comment dictionaries.

    try:
        # Keep requesting pages until:
        # - we have enough comments, or
        # - there are no more pages
        while len(comments) < max_comments:
            fetch_count = min(100, max_comments - len(comments))
 # YouTube allows up to 100 comments per API request.
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=fetch_count,
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )
            response = request.execute()

# Extract each top-level comment from the response.
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

                # stop early if we already reached the maximum requested
                if len(comments) >= max_comments:
                    break

              # get token for the next page of results, if one exists
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                # No more pages available.
                break

    except Exception as e:
        if "commentsDisabled" in str(e):
            # commentsDisabled is a common API case and not really a serious error.
       
            print(f"  [INFO] Comments are disabled for {video_id}")
        else:
            print(f"  [WARNING] Error fetching comments for {video_id}: {e}")

    return comments

# converts youtube's weird ISO8601 duration format (PT1H2M3S) into total seconds
def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0

# convert a YouTube duration string such as 'PT1H2M3S' into total seconds.

#     Example:
#         'PT1H2M3S' -> 3723
#         'PT15M' -> 900
#         'PT45S' -> 45

#     Why this is useful:
#     - the API gives duration in ISO 8601 format, which is not very easy
#       to compare or analyse directly, so i translated out into total seconds
#     - total seconds are easier for calculations and plotting.

    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    # Regex groups:
    # (\d+)H = hours
    # (\d+)M = minutes
    # (\d+)S = seconds

    if not match:
        return 0
   # if a part is missing, use 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds

# formats seconds into human readable HH:MM:SS or MM:SS
def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    # Convert total seconds into:
    # - HH:MM:SS if there is at least 1 hour
    # - MM:SS otherwise

    # Example:
    #     3723 -> '01:02:03'
    #     125 -> '02:05'

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

# dumps all collected data for one video into its own folder
def save_video_data(output_dir: str, video_id: str, metadata: dict,
                    transcript_text: str, transcript_segments: list,
                    comments: list) -> None:
    """saves metadata, transcript, and comments as separate files in a
    per-video directory under the output folder."""
    video_dir = os.path.join(output_dir, video_id)
    os.makedirs(video_dir, exist_ok=True)

    # - Each video gets its own folder, which keeps the dataset organised.
    # - Different data types are stored separately, making them easier to inspect,
    #   debug, or reuse later in the pipeline

    if metadata:  # save metadata if it exists
        with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

     if transcript_text: #save full transcript text as plain text for easy reading
        with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
            f.write(transcript_text)

    if transcript_segments: #Save timestamped transcript segments as JSON
        with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
            json.dump(transcript_segments, f, indent=2, ensure_ascii=False)

    if comments:   # Save comments as JSON
        with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2, ensure_ascii=False)

    print(f"  [SAVED] Data saved to {video_dir}")
