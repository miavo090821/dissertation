# step 5: algospeak detection
#
# 1. this script detects coded language (algospeak) that creators and viewers may use to avoid platform filters
# 2. it checks both transcripts and comments using regex word-boundary matching

# 3. when a term is found, it saves nearby text as context so we can manually verify it later
# 4. it separates creator vs viewer use in comments, which is useful for the research questions

# 5. it supports:
#    - --archive to back up old outputs before running again
#    - --skip-existing to continue from where a previous run stopped

# 6. it outputs:
#    - a detailed csv of every algospeak finding
#    - a summary csv with one row per video

# sys is used for system-level actions, such as exiting the script if something goes wrong
import sys

# os is used for working with folders, file paths, and checking whether files exist
import os

# csv is used to read and write csv output files
import csv

# json is used to load comment files and metadata stored in json format
import json

# re is python's regular expression module, used here to match algospeak terms safely
import re

# argparse lets us add command-line options like --archive and --skip-existing
import argparse

# datetime is used to create timestamped archive folder names
from datetime import datetime

# add parent directory to the system path so python can import config and project utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import the main data folders and output filename from config.py
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, ALGOSPEAK_FINDINGS_FILE
except ImportError:
    # stop the script if config.py cannot be found
    print("ERROR: config.py not found!")
    sys.exit(1)

# import the algospeak dictionary, category list, and helper function
from scripts.utils.algospeak_dict import (
    ALGOSPEAK_DICT,
    ALGOSPEAK_CATEGORIES,
    get_category
)

def get_extracted_videos(raw_dir: str) -> list:
    # this function finds all video folders that already contain transcript or comment data
    if not os.path.exists(raw_dir):
        return []
    
    video_ids = []
    
    for item in os.listdir(raw_dir):
        item_path = os.path.join(raw_dir, item)
        
        if os.path.isdir(item_path):
            # check whether this video folder has either a transcript or comments
            has_transcript = os.path.exists(os.path.join(item_path, 'transcript.txt'))
            has_comments = os.path.exists(os.path.join(item_path, 'comments.json'))
            
            if has_transcript or has_comments:
                video_ids.append(item)
    
    # sort the ids to keep processing order tidy and consistent
    return sorted(video_ids)


def load_transcript(raw_dir: str, video_id: str) -> str:
    # this function loads the transcript text for one video
    transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
    
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # return an empty string if no transcript exists
    return ""


def load_comments(raw_dir: str, video_id: str) -> list:
    # this function loads comments for one video, including replies
    comments_path = os.path.join(raw_dir, video_id, 'comments.json')
    
    if os.path.exists(comments_path):
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # flatten the structure so top-level comments and replies are all in one list
        all_comments = []
        for comment in comments:
            all_comments.append(comment)
            for reply in comment.get('replies', []):
                all_comments.append(reply)
        
        return all_comments
    
    # return an empty list if there is no comments file
    return []


def load_metadata(raw_dir: str, video_id: str) -> dict:
    # this function loads metadata such as title, channel id, and publication date
    metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # return an empty dictionary if metadata is missing
    return {}


def detect_algospeak_with_boundaries(text: str) -> list:
    # this function looks for algospeak terms in a piece of text
    # it returns a list of findings, including:
    # - the term
    # - its original meaning
    # - its category
    # - how many times it appeared
    # - some context snippets around the matches
    if not text:
        return []
    
    text_lower = text.lower()
    results = []
    
    for term, meaning in ALGOSPEAK_DICT.items():
        term_lower = term.lower()
        
        # build the regex pattern
        # phrases with spaces or hyphens are matched directly
        # single words use word boundaries so we do not match parts of larger words by mistake
        if ' ' in term_lower or '-' in term_lower:
            pattern = re.escape(term_lower)
        else:
            pattern = r'\b' + re.escape(term_lower) + r'\b'
        
        matches = list(re.finditer(pattern, text_lower))
        count = len(matches)
        
        if count > 0:
            # save a few context windows so we can inspect how the term was actually used
            contexts = []
            for match in matches[:3]:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippet = text[start:end].replace('\n', ' ').strip()
                
                # add ... if the context is clipped at the start or end
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                contexts.append(snippet)
            
            results.append({
                'term': term,
                'meaning': meaning,
                'category': get_category(term),
                'count': count,
                'contexts': contexts
            })
    
    # sort so the most frequent algospeak terms appear first
    return sorted(results, key=lambda x: x['count'], reverse=True)


def archive_output(output_dir: str) -> str:
    # this function makes a backup copy of the current output folder
    # it saves the backup inside an archive folder with a timestamped name
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        return None
    
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = os.path.join(archive_dir, f'run_{timestamp}')
    
    # import shutil here because it is only needed for archiving
    import shutil
    
    # copy the full output folder into the archive location
    shutil.copytree(output_dir, archive_path)
    
    return archive_path


def main():
    # set up command-line arguments for optional behaviour
    parser = argparse.ArgumentParser(description='Detect algospeak in transcripts and comments')
    parser.add_argument('--archive', action='store_true', help='Archive previous output before running')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip videos already in existing output')
    args = parser.parse_args()
    
    # build the main folder and file paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_path = os.path.join(output_dir, ALGOSPEAK_FINDINGS_FILE)
    
    # if --archive is used, back up the previous output first
    if args.archive:
        archive_path = archive_output(output_dir)
        if archive_path:
            print(f"[ARCHIVED] Previous output saved to: {archive_path}")
    
    # get all videos that have transcript or comment data available
    video_ids = get_extracted_videos(raw_dir)

    # if --skip-existing is used, load previous outputs and skip videos already processed
    existing_findings = []
    existing_summaries = []
    
    if args.skip_existing:
        summary_path = output_path.replace('.csv', '_summary.csv')
        
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_summaries = list(reader)
            
            existing_ids = {row['video_id'] for row in existing_summaries}

            # also load the old detailed findings so they can be merged back in later
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_findings = list(reader)

            before = len(video_ids)
            video_ids = [v for v in video_ids if v not in existing_ids]
            print(f"  Skip-existing: {before - len(video_ids)} already processed, {len(video_ids)} new")

    # stop if there is no extracted data at all
    if not video_ids and not existing_summaries:
        print("ERROR: No extracted videos found")
        print("Please run step2_batch_extract.py first")
        sys.exit(1)
    
    # print a simple overview before processing starts
    print("STEP 5: ALGOSPEAK DETECTION")
    print(f"Videos: {len(video_ids)} | Algospeak terms: {len(ALGOSPEAK_DICT)}\n")
    
    # make sure the output folder exists
    os.makedirs(output_dir, exist_ok=True)
    
    # these lists will store:
    # - every detailed algospeak finding
    # - one summary row per video
    all_findings = []
    video_summaries = []
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Scanning: {video_id}")
        
        transcript = load_transcript(raw_dir, video_id)
        comments = load_comments(raw_dir, video_id)
        metadata = load_metadata(raw_dir, video_id)
        channel_id = metadata.get('channel_id', '')
        
        # counters for transcript and comments
        transcript_instances = 0
        transcript_unique = 0
        comment_instances = 0
        comment_unique = 0
        creator_comment_instances = 0
        

        # process transcript text
        if transcript:
            transcript_findings = detect_algospeak_with_boundaries(transcript)
            transcript_instances = sum(f['count'] for f in transcript_findings)
            transcript_unique = len(transcript_findings)
            
            # save one row per context snippet for each transcript term found
            for term_data in transcript_findings:
                for context in term_data.get('contexts', ['No context']):
                    all_findings.append({
                        'video_id': video_id,
                        'video_title': metadata.get('title', '')[:50],
                        'source': 'transcript',
                        'is_creator': True,
                        'algospeak_term': term_data['term'],
                        'original_meaning': term_data['meaning'],
                        'category': term_data['category'],
                        'occurrences': term_data['count'],
                        'context': context
                    })
        

        # process comments
 # this dictionary tracks total counts per algospeak term across all comments in one video
        comment_term_counts = {}
        
        for comment in comments:
            text = comment.get('text', '')
            
    # identify whether this comment was posted by the creator or a viewer
            is_creator = comment.get('author_channel_id', '') == channel_id
            
            comment_findings = detect_algospeak_with_boundaries(text)
            
            for term_data in comment_findings:
                term = term_data['term']
                
        # add this term's count into the per-video comment totals
                comment_term_counts[term] = comment_term_counts.get(term, 0) + term_data['count']
                
    # track how many algospeak instances specifically came from the creator
                if is_creator:
                    creator_comment_instances += term_data['count']
                
         # save one detailed row for each context snippet
                for context in term_data.get('contexts', ['No context']):
                    all_findings.append({
                        'video_id': video_id,
                        'video_title': metadata.get('title', '')[:50],
                        'source': 'comment',
                        'is_creator': is_creator,
                        'algospeak_term': term_data['term'],
                        'original_meaning': term_data['meaning'],
                        'category': term_data['category'],
                        'occurrences': term_data['count'],
                        'context': context
                    })
        
    # calculate total algospeak use in comments for this video
        comment_instances = sum(comment_term_counts.values())
        comment_unique = len(comment_term_counts)
        
        # save one summary row for this video
        video_summaries.append({
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'published_at': metadata.get('published_at', '')[:10] if metadata.get('published_at') else '',
            'transcript_instances': transcript_instances,

            'transcript_unique_terms': transcript_unique,
            'comment_instances': comment_instances,
            'comment_unique_terms': comment_unique,
            'creator_comment_instances': creator_comment_instances,
            'total_instances': transcript_instances + comment_instances
        })
        
    # print progress for the current video
        print(f"  Transcript: {transcript_instances} instances ({transcript_unique} unique)")
        print(f"  Comments: {comment_instances} instances ({comment_unique} unique, creator: {creator_comment_instances})")
    
# if skip-existing was used, add the old rows back in so the new csvs contain everything
    all_findings = existing_findings + all_findings
    video_summaries = existing_summaries + video_summaries

# write the full detailed findings csv
    if all_findings:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_findings[0].keys()))
            writer.writeheader()
            writer.writerows(all_findings)
        print(f"\nSUCCESS: Detailed findings saved to {output_path}")
    
# write the per-video summary csv
    summary_path = output_path.replace('.csv', '_summary.csv')
    if video_summaries:
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(video_summaries[0].keys()))
            writer.writeheader()
            writer.writerows(video_summaries)
        print(f"SUCCESS: Video summary saved to {summary_path}")
    
# compute totals across all videos
    # int() is used because rows loaded from an existing csv come in as strings
    total_transcript = sum(int(v['transcript_instances']) for v in video_summaries)
    total_comment = sum(int(v['comment_instances']) for v in video_summaries)
    total_creator_comment = sum(int(v['creator_comment_instances']) for v in video_summaries)
    
    print(f"\nSummary: {len(video_summaries)} videos | Transcript: {total_transcript} | Comments: {total_comment}")
    print(f"Creator comments: {total_creator_comment} | Viewer comments: {total_comment - total_creator_comment}")
    print("Next: Run step6_generate_report.py")

if __name__ == "__main__":
    # run the main function only when this file is executed directly
    main()