# step 2: batch extract all videos
#
# 1. this script reads video_urls.csv and loops through every video one by one
# 2. for each video, it collects metadata from the youtube data api, transcript data from supadata, and comments from youtube
# 3. all outputs are saved into a separate folder for each video under data/raw/{video_id}/
# 4. this makes the dataset organised and easier to use in later steps of the pipeline
# 5. --skip-existing is useful if the script crashes halfway through, because it lets us continue without re-downloading finished files
# 6. supadata is used for transcripts because it is more reliable for this project than youtube's own transcript access
# 7. overall, this step is basically the raw data collection stage for the whole research pipeline

import sys        
# lets the script interact with python system settings, for example sys.exit()
import os         
# used for file paths and checking whether folders or files exist
import json       
# helps save and load structured data in json format
import re         
# used for pattern matching in strings, such as finding a video id in a youtube link
import csv        
# used to open and read the input csv file row by row
import time       
# mainly used for sleep delays so requests are not sent too quickly
import argparse   
# used so we can run the script with options from the command line
import requests   
# makes web requests to apis, for example when fetching transcripts from supadata


# ensure the parent directory of the scripts folder is on the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# compute project base directory from this file location, this gives the main dissertation/project folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# add base directory to sys.path so config and other modules can be imported
# without this, imports may fail depending on where the script is launched from
sys.path.insert(0, base_dir)

try:
    # import configuration values and constants
    # these are the shared settings used across the whole project
    from config import (
        YOUTUBE_API_KEY,
        DATA_RAW_DIR,
        DATA_INPUT_DIR,
        MAX_COMMENTS_PER_VIDEO,
        SUPADATA_API_KEY,
        SUPADATA_BASE_URL
    )

except ImportError as e:
    # this happens if config.py cannot be found at all
    print(f"ERROR: Could not import config.py")
    print(f"Expected location: {os.path.join(base_dir, 'config.py')}")
    print(f"Make sure you're running from the dissertation directory")
    sys.exit(1)

except SystemExit:
    # allow explicit system exit to propagate normally
    raise

except Exception as e:
    # this catches other config-related problems, such as missing variables inside config.py
    print(f"ERROR: config.py found but failed to load: {e}")
    sys.exit(1)

# import YouTube Data API client
# this is the main client used to talk to youtube's official api
from googleapiclient.discovery import build

def extract_video_id(url_or_id: str) -> str:
    # this function tries to turn a youtube url into just the 11-character video id
 # if the input is already just an id, it returns it unchanged
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]

    # check the input against each possible pattern
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            # the video id is stored in the first captured group
            return match.group(1)

    # if nothing matches, return the original input
    # this is a safe fallback so the script does not immediately break
    return url_or_id


def get_video_metadata(youtube, video_id: str) -> dict:
    # fetch metadata for a single video from the youtube data api
    # metadata includes things like title, description, view count, likes, and publish date
    try:
        # build request to retrieve snippet, statistics, content details, and status
        print(f"    Fetching metadata from YouTube API...", end="", flush=True)
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=video_id
        )

        # send the request to youtube
        response = request.execute()
        print(" done", flush=True)

# make sure youtube returned at least one video item
        if response['items']:
            item = response['items'][0]

        # snippet contains basic descriptive information
            snippet = item['snippet']

    # statistics contains numeric counters like views and likes
            stats = item['statistics']

        # contentDetails contains things like duration
            content = item['contentDetails']

    # return a cleaned metadata dictionary
        # this makes the data easier to save and use later
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
        # report any metadata error but let the script continue with later videos
        print(f"    Metadata error: {e}")

    # return None if metadata could not be retrieved
    return None


def get_transcript_supadata(video_id: str) -> tuple:
# fetch transcript for one video using supadata
    # this function returns:
    # 1. the full plain transcript text
    # 2. a list of timestamped transcript segments

    # build the normal youtube watch url because supadata expects a full url
    url = f"https://www.youtube.com/watch?v={video_id}"

    # first request asks for the plain text transcript
    params = {
        "url": url,
        "lang": "en",
        "text": "true",
        "mode": "native"
    }

    # api key goes in the request header
    headers = {"x-api-key": SUPADATA_API_KEY}

    try:
# request full transcript text
        print(f"    Fetching transcript from Supadata...", end="", flush=True)
        response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=15)
        print(" done", flush=True)

    # if request succeeded, parse the transcript response
        if response.status_code == 200:
            data = response.json()

        # "content" stores the plain text transcript in this mode
            content = data.get("content", "")

            if content:
        # now request timestamped segments as a second call
        # here "text" is switched to false so the api returns structured segments instead
                params["text"] = "false"
                seg_response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)

                segments = []

        # if the second request also works, try to build clean segment objects
                if seg_response.status_code == 200:
                    seg_data = seg_response.json()
                    raw_segments = seg_data.get("content", [])

            # make sure the returned content is actually a list
                    if isinstance(raw_segments, list):
                        for seg in raw_segments:
            # convert milliseconds into seconds because seconds are easier to work with later
                            segments.append({
                                "text": seg.get("text", ""),
                                "start": seg.get("offset", 0) / 1000,
                                "duration": seg.get("duration", 0) / 1000
                            })

        # return both transcript text and time-coded segments
                return content, segments

    # if we hit rate limiting, wait and retry
        elif response.status_code == 429:
            print("    Rate limited waiting 10 seconds")
            time.sleep(10)
            return get_transcript_supadata(video_id)

    except Exception as e:
    # catch transcript errors without stopping the whole batch
        print(f"    Transcript error: {e}")

    # if transcript could not be fetched, return empty placeholders
    return None, None


def get_comments_with_replies(youtube, video_id: str, max_comments: int = 200) -> list:
# fetch top-level comments and any replies for a single video
    # comments are useful later for audience reaction analysis
    comments = []

    # youtube comments are paginated, so we use this token to move through pages
    next_page_token = None

    try:
        print(f"    Fetching comments from YouTube API...", end="", flush=True)

    # keep requesting until we either reach the comment limit or run out of pages
        while len(comments) < max_comments:
            # request one page of comment threads
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )

            # send request to youtube
            response = request.execute()

    # go through each comment thread in this page
            for item in response.get('items', []):
        # topLevelComment is the main parent comment
                top_comment = item['snippet']['topLevelComment']
                snippet = top_comment['snippet']

        # total number of replies linked to this comment
                total_reply_count = item['snippet'].get('totalReplyCount', 0)

            # build a clean structure for this parent comment
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

        # if the comment has replies, try to collect them as well
                if total_reply_count > 0:
            # sometimes youtube already includes replies inside the same response
                    included_replies = item.get('replies', {}).get('comments', [])

            # if all replies are already present, use them directly
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
        # otherwise, make a second request to fetch more replies
                        try:
                            reply_request = youtube.comments().list(
                                part="snippet",
                                parentId=top_comment['id'],
                                maxResults=min(50, total_reply_count),
                                textFormat="plainText"
                            )
                            reply_response = reply_request.execute()

                # add each reply into the nested replies list
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

    # small pause so we are a bit gentler with the api
                            time.sleep(0.1)

                        except Exception:
    # if reply fetching fails, ignore it so the main comment still gets saved
                            pass

                # add this full comment thread to the output list
                comments.append(comment_data)

                # stop early if we already have enough comments
                if len(comments) >= max_comments:
                    break

            # get token for the next page of comments
            next_page_token = response.get('nextPageToken')

            # if there is no next page token, we reached the end
            if not next_page_token:
                break

        # print total number of collected comments
        print(f" ({len(comments)} comments)", flush=True)

    except Exception as e:
        # commentsDisabled is normal for some videos, so treat it differently
        if "commentsDisabled" not in str(e):
            print(f"    Comments error: {e}", flush=True)
        else:
            print(" (disabled)", flush=True)

    # return all collected comments, possibly with nested replies
    return comments


def load_video_list(input_dir: str) -> list:
    # load the video list from video_urls.csv
    # this function is a bit defensive because csv column names can sometimes be messy
    csv_path = os.path.join(input_dir, 'video_urls.csv')

    # stop immediately if the csv file does not exist
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found!")
        sys.exit(1)

    videos = []

    # utf-8-sig helps handle files that may contain a byte order mark
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        # read each row from the csv
        for row in reader:
            url = None

            # first, try to find a clean column literally called url
            for key in row.keys():
                key_clean = key.strip().lstrip('\ufeff').lower()
                if key_clean == 'url':
                    url = row[key]
                    break

            # fallback to a few common alternative column names
            if not url:
                url = row.get('url') or row.get('URL') or row.get('video_url')

            # last fallback: accept any column name containing the word "url"
            if not url:
                for key in row.keys():
                    if 'url' in key.lower():
                        url = row[key]
                        break

            # only keep rows where we actually found a non-empty url
            if url and url.strip():
                video_id = extract_video_id(url)

                # store the normalised video id, original url,
                # and any other extra columns that may be useful later
                videos.append({
                    'video_id': video_id,
                    'url': url,
                    **{
                        k: v
                        for k, v in row.items()
                        if k not in ['url', 'URL', 'video_url', '\ufeffurl'] and not k.startswith('\ufeff')
                    }
                })

    return videos


def main():
    # create command-line arguments for this batch extraction step
    parser = argparse.ArgumentParser(description='Batch extract video data')

    # if turned on, do not re-download files that already exist
    parser.add_argument('--skip-existing', action='store_true', help='Skip videos with existing data')

    # delay between transcript requests helps avoid stressing supadata too much
    parser.add_argument('--transcript-delay', type=int, default=3, help='Delay between transcript fetches (default: 3s)')

    # lets us control how many comments we want per video
    parser.add_argument('--max-comments', type=int, default=200, help='Max comments per video (default: 200)')

    # read the arguments provided when running the script
    args = parser.parse_args()

    # recompute base directory in case the file is moved or run from somewhere else
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # raw_dir is where all per-video folders will be created
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)

    # input_dir is where video_urls.csv should be located
    input_dir = os.path.join(base_dir, DATA_INPUT_DIR)

    # load list of videos from the input csv
    videos = load_video_list(input_dir)

    # if nothing was loaded, stop here
    if not videos:
        print("ERROR: No videos found in video_urls.csv")
        sys.exit(1)

    # print a quick summary before starting
    print("STEP 2: BATCH EXTRACT ALL VIDEOS")
    print(f"Videos: {len(videos)} | Delay: {args.transcript_delay}s | Max comments: {args.max_comments}")
    print(f"Skip existing: {args.skip_existing}\n")

    # build youtube api client using the api key from config.py
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # keep track of success/failure/skip counts for each component
    stats = {
        'metadata': {'success': 0, 'failed': 0, 'skipped': 0},
        'transcript': {'success': 0, 'failed': 0, 'skipped': 0},
        'comments': {'success': 0, 'failed': 0, 'skipped': 0}
    }

    # loop through all videos in the input list
    for i, video in enumerate(videos, 1):
        video_id = video['video_id']

        # create a dedicated folder for this video's raw files
        video_dir = os.path.join(raw_dir, video_id)
        os.makedirs(video_dir, exist_ok=True)

        # progress label so we can see where we are in the batch
        print(f"\n[{i}/{len(videos)}] {video_id}")

        # check whether files already exist for this video
        has_metadata = os.path.exists(os.path.join(video_dir, 'metadata.json'))
        has_transcript = os.path.exists(os.path.join(video_dir, 'transcript.txt'))
        has_comments = os.path.exists(os.path.join(video_dir, 'comments.json'))


        # metadata stage
        if args.skip_existing and has_metadata:
            # skip metadata if file already exists and skip mode is on
            print("  [Metadata] Skipped")
            stats['metadata']['skipped'] += 1
        else:
            # fetch metadata from youtube
            metadata = get_video_metadata(youtube, video_id)

            if metadata:
                # also add any extra columns from video_urls.csv into the saved metadata
                metadata.update({k: v for k, v in video.items() if k not in ['video_id', 'url']})

                # save metadata to json
                with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # show part of the title as a quick sense check
                print(f"  [Metadata] {metadata['title'][:40]}...")
                print("  SUCCESS: Metadata saved")
                stats['metadata']['success'] += 1
            else:
                print("  [Metadata] ERROR: Failed")
                stats['metadata']['failed'] += 1


        # transcript stage
        if args.skip_existing and has_transcript:
            # skip transcript if already saved
            print("  [Transcript] Skipped")
            stats['transcript']['skipped'] += 1
        else:
            # fetch transcript text and timestamped segments from supadata
            transcript_text, segments = get_transcript_supadata(video_id)

            if transcript_text:
                # save plain transcript text
                with open(os.path.join(video_dir, 'transcript.txt'), 'w', encoding='utf-8') as f:
                    f.write(transcript_text)

                # if timestamped segments exist, save them separately as json
                if segments:
                    with open(os.path.join(video_dir, 'transcript_segments.json'), 'w', encoding='utf-8') as f:
                        json.dump(segments, f, indent=2, ensure_ascii=False)

                # quick word count check helps confirm transcript looks reasonable
                print(f"  [Transcript] {len(transcript_text.split()):,} words")
                print("  SUCCESS: Transcript saved")
                stats['transcript']['success'] += 1

            else:

                # transcript may genuinely be unavailable for some videos
                print("  [Transcript] WARNING: Not available")
                stats['transcript']['failed'] += 1

            # delay between transcript requests to reduce pressure on the transcript service
            if i < len(videos):
                time.sleep(args.transcript_delay)


        # comments stage
        if args.skip_existing and has_comments:
            # skip comments if already saved
            print("  [Comments] Skipped")
            stats['comments']['skipped'] += 1
        else:
            # fetch comments and replies
            comments = get_comments_with_replies(youtube, video_id, max_comments=args.max_comments)

            if comments:
                # save comments as json
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump(comments, f, indent=2, ensure_ascii=False)

                # count total replies across all parent comments
                total_replies = sum(len(c.get('replies', [])) for c in comments)
                print(f"  [Comments] {len(comments)} comments, {total_replies} replies")
                print("  SUCCESS: Comments saved")
                stats['comments']['success'] += 1
            else:
                # even if there are no comments, save an empty file so later steps still work cleanly
                with open(os.path.join(video_dir, 'comments.json'), 'w', encoding='utf-8') as f:
                    json.dump([], f)

                print("  [Comments] WARNING: None available")
                stats['comments']['failed'] += 1

        # short pause between videos so requests are not too aggressive
        time.sleep(0.5)

    # final summary after all videos have been processed
    print("\nCOMPLETE")
    print(f"{'Component':<15} {'Success':>10} {'Failed':>10} {'Skipped':>10}")
    print("-" * 45)

    for component, counts in stats.items():
        print(f"{component.capitalize():<15} {counts['success']:>10} {counts['failed']:>10} {counts['skipped']:>10}")

    # show where the raw files were saved
    print(f"\nOutput: {raw_dir}")
    print("Next: Run step3_sensitivity_analysis.py")


if __name__ == "__main__":
    # run main() only when this file is executed directly
    # this prevents it from running automatically if imported from another file
    main()