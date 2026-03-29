# step 4: comments analysis (rq2 - perception)
#
# 1. this script looks through youtube comments for words related to monetisation perception
# 2. it uses regex word boundaries so it only matches full words, not parts of other words
# 3. it separates creator comments from viewer comments so both groups can be analysed separately
# 4. it produces two csv files:
#    - one with every matched comment
#    - one with a summary for each video
# 5. the perception keywords are loaded from a json dictionary in the dictionaries folder

# sys lets us interact with the python system, for example exiting the script if something goes wrong
import sys

# os is used for working with file paths, folders, and checking whether files exist
import os

# csv is used to write the final analysis results into csv output files
import csv

# json is used to load the keyword dictionary and comment/metadata files
import json

# re is python's regular expression module, used here for keyword matching with word boundaries
import re

# add parent directory to the system path so internal modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import project-wide configuration paths and filenames
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DICTIONARIES_DIR, COMMENTS_ANALYSIS_FILE
except ImportError:
    # stop the script if config.py cannot be found, because the file paths are needed
    print("ERROR: config.py not found!")
    sys.exit(1)


def load_perception_keywords(dictionaries_dir: str) -> dict:
    # this function loads the monetisation perception keywords from a json file
    keywords_path = os.path.join(dictionaries_dir, 'perception_keywords.json')
    
    if not os.path.exists(keywords_path):
        # if the file is missing, print a warning and return an empty dictionary
        print(f"WARNING: {keywords_path} not found")
        return {}
    
    # open and read the json file
    with open(keywords_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # this will store the final clean keyword dictionary
    keywords_dict = {}
    
    # support both possible json structures:
    # either everything is directly in the file, or inside a "categories" key
    categories = data.get('categories', data)
    
    for category_name, category_data in categories.items():
        # if the category is stored as a dictionary with a "keywords" field, use that
        if isinstance(category_data, dict) and 'keywords' in category_data:
            keywords_dict[category_name] = category_data['keywords']
        
        # if the category is already just a list of keywords, use it directly
        elif isinstance(category_data, list):
            keywords_dict[category_name] = category_data
    
    return keywords_dict


def get_extracted_videos(raw_dir: str) -> list:
    # this function finds all video folders that contain a comments.json file
    # those are the videos that already have extracted comments and can be analysed
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        
        # only check folders, because each video should have its own folder
        if os.path.isdir(item_path):
            comments_path = os.path.join(item_path, 'comments.json')
            
            # if comments.json exists, add this video id to the list
            if os.path.exists(comments_path):
                video_ids.append(item)
    
    # return video ids in sorted order for cleaner output
    return sorted(video_ids)


def load_comments(raw_dir: str, video_id: str) -> list:
    # this function loads all comments for one video
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # comments.json may contain top-level comments with replies nested inside
        # this part flattens everything into one list so all comments can be checked equally
        all_comments = []
        
        for comment in comments:
            all_comments.append(comment)
            all_comments.extend(comment.get('replies', []))
        
        return all_comments
    
    # if the file does not exist, return an empty list
    return []


def load_metadata(raw_dir: str, video_id: str) -> dict:
    # this function loads metadata for a video, such as title and channel information
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # if metadata is missing, return an empty dictionary instead of crashing
    return {}


def search_comment_with_word_boundaries(text: str, keywords_dict: dict) -> list:
    # this function checks one comment for any perception keywords
    # it returns a list of matches in the form (category, keyword)
    text_lower = text.lower()
    matches = []
    
    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # if a keyword has spaces or hyphens, simple substring matching is used
            # this is easier for phrases like "not monetized" or "de-monetised"
            if ' ' in keyword_lower or '-' in keyword_lower:
                if keyword_lower in text_lower:
                    matches.append((category, keyword))
            else:
                # for single words, use regex word boundaries
                # this avoids false matches such as matching "ad" inside "shadow"
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, text_lower):
                    matches.append((category, keyword))
    
    return matches


def is_creator_comment(comment: dict, channel_id: str) -> bool:
    # this function checks whether a comment was posted by the video creator
    # it does this by comparing the author's channel id with the video's channel id
    author_channel_id = comment.get('author_channel_id', '')
    return author_channel_id == channel_id


def main():
    # build the main folder paths used in the script
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dictionaries_dir = os.path.join(base_dir, DICTIONARIES_DIR)
    output_path = os.path.join(output_dir, COMMENTS_ANALYSIS_FILE)
    
    # load the perception keyword categories from the json file
    PERCEPTION_KEYWORDS = load_perception_keywords(dictionaries_dir)
    
    if not PERCEPTION_KEYWORDS:
        # stop if no keywords were loaded, because the analysis cannot continue without them
        print("ERROR: No perception keywords loaded")
        print(f"Check: {os.path.join(dictionaries_dir, 'perception_keywords.json')}")
        sys.exit(1)
    
    # get all video ids that already have extracted comments
    video_ids = get_extracted_videos(raw_dir)
    
    if not video_ids:
        # stop if no comments data is available yet
        print("ERROR: No videos with comments found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    # print a simple overview of what will be analysed
    print("STEP 4: COMMENTS PERCEPTION ANALYSIS")
    total_keywords = sum(len(kw) for kw in PERCEPTION_KEYWORDS.values())
    print(f"Videos: {len(video_ids)} | Categories: {len(PERCEPTION_KEYWORDS)} | Keywords: {total_keywords}\n")
    
    # create the output folder if it does not already exist
    os.makedirs(output_dir, exist_ok=True)
    
    # these lists will store:
    # - all matched comments in detail
    # - one summary row per video
    all_matches = []
    video_summaries = []
    
    # these counters track totals across the whole dataset
    total_creator_comments = 0
    total_creator_matches = 0
    total_viewer_comments = 0
    total_viewer_matches = 0
    
    for i, video_id in enumerate(video_ids, 1):
        # process one video at a time
        print(f"[{i}/{len(video_ids)}] Analyzing comments: {video_id}")
        
        comments = load_comments(raw_dir, video_id)
        metadata = load_metadata(raw_dir, video_id)
        channel_id = metadata.get('channel_id', '')
        channel_name = metadata.get('channel_name', '')
        
        if not comments:
            # skip videos where no comments were loaded
            print(f"  SKIP: No comments")
            continue
        
        # these counters are for just this one video
        video_matches = 0
        creator_matches = 0
        viewer_matches = 0
        creator_comment_count = 0
        
        # set up a counter for each perception category
        category_counts = {cat: 0 for cat in PERCEPTION_KEYWORDS.keys()}
        
        for comment in comments:
            text = comment.get('text', '')
            is_reply = comment.get('is_reply', False)
            is_creator = is_creator_comment(comment, channel_id)
            
            # count how many total creator comments there are
            if is_creator:
                creator_comment_count += 1
            
            # search the current comment for perception-related keywords
            matches = search_comment_with_word_boundaries(text, PERCEPTION_KEYWORDS)
            
            if matches:
                # this comment contains at least one perception keyword
                video_matches += 1
                
                # keep track of whether the match came from the creator or a viewer
                if is_creator:
                    creator_matches += 1
                else:
                    viewer_matches += 1
                
                # remove duplicates so the same category/keyword is not repeated in one comment
                categories_found = list(set([m[0] for m in matches]))
                keywords_found = list(set([m[1] for m in matches]))
                
                # increase the count for each category found in this comment
                for cat in categories_found:
                    category_counts[cat] += 1
                
                # save one detailed output row for this matched comment
                all_matches.append({
                    'video_id': video_id,
                    'video_title': metadata.get('title', '')[:50],
                    'is_creator': is_creator,
                    'is_reply': is_reply,
                    'comment_author': comment.get('author', ''),
                    'comment_likes': comment.get('like_count', 0),
                    'comment_text': text[:500].replace('\n', ' '),
                    'categories_matched': ', '.join(categories_found),
                    'keywords_matched': ', '.join(keywords_found)
                })
        
        # update the overall totals after finishing this video
        total_creator_comments += creator_comment_count
        total_creator_matches += creator_matches
        total_viewer_comments += len(comments) - creator_comment_count
        total_viewer_matches += viewer_matches
        
        # save one summary row for this video
        video_summaries.append({
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'channel_name': channel_name,
            'total_comments': len(comments),
            'creator_comments': creator_comment_count,
            'perception_comments': video_matches,
            'creator_perception': creator_matches,
            'viewer_perception': viewer_matches,
            'perception_ratio': round(video_matches / len(comments) * 100, 2) if comments else 0,
            **{f'{cat}_mentions': count for cat, count in category_counts.items()}
        })
        
        # print a short progress summary for this video
        print(f"  Comments: {len(comments)} (creator: {creator_comment_count}) | "
              f"Perception: {video_matches} (creator: {creator_matches}, viewers: {viewer_matches})")
    
    # write the detailed matched comments to csv
    if all_matches:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_matches[0].keys()))
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"\nSUCCESS: Detailed matches saved to {output_path}")
    
    # write the per-video summary csv
    summary_path = output_path.replace('.csv', '_summary.csv')
    if video_summaries:
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(video_summaries[0].keys()))
            writer.writeheader()
            writer.writerows(video_summaries)
        print(f"SUCCESS: Video summary saved to {summary_path}")
    
    # compute totals across all videos for the final printout
    total_perception = sum(v['perception_comments'] for v in video_summaries)
    total_comments = sum(v['total_comments'] for v in video_summaries)
    
    print(f"\nSummary: {total_comments:,} comments analyzed | {total_perception} with perception keywords")
    print(f"Creator: {total_creator_matches}/{total_creator_comments} | Viewer: {total_viewer_matches}/{total_viewer_comments:,}")
    print("Next: Run step5_algospeak_detection.py")


if __name__ == "__main__":
    # run the main function only when this file is executed directly
    main()