# step 3b: category cross-analysis
#
# 1. this script compares transcript content using two different dictionaries:
#    sensitive words and algospeak terms
# 2. instead of only counting exact words overall, it groups matches into categories
#    such as violence, drugs, or sexual content
# 3. this helps show whether certain topics appear more often in videos that are
#    monetised or demonetised
# 4. it uses the sensitive words dictionary and the algospeak dictionary together
#    so both types of language can be analysed side by side
# 5. the final output is a csv file with category-level counts for each video

# sys lets the script exit safely and also helps with Python path handling
import sys

# os is used for working with folders and file paths
import os

# csv is used to read from and write to csv files
import csv

# json is used to load metadata files such as video title and channel name
import json

# this adds the parent project folder to the Python path
# so the script can import config.py and utility files correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import folder locations from the main config file
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR, DICTIONARIES_DIR
except ImportError:
    # stop the script if config.py cannot be found
    print("ERROR: config.py not found!")
    sys.exit(1)

# import NLP helper functions from the utils folder
from scripts.utils.nlp_processor import (
    # analyses transcript matches grouped by sensitive-word category
    analyze_transcript_by_category,

    # imported from utils for consistency with the project, even though it is not used directly here
    clean_and_lemmatize,

    # imported from utils for consistency with the project, even though it is not used directly here
    count_sensitive_matches,
)


def load_algospeak_dict():
    # try to load the algospeak dictionary and its category lookup function
    try:
        from scripts.utils.algospeak_dict import ALGOSPEAK_DICT, get_category
        return ALGOSPEAK_DICT, get_category
    except ImportError:
        # if the algospeak file cannot be loaded, continue with an empty dictionary
        print("WARNING: Could not import algospeak dictionary")
        return {}, lambda t: 'uncategorised'


def count_algospeak_by_category(text: str, algospeak_dict: dict, get_category_fn) -> dict:
    # count how many algospeak terms appear in the transcript for each category
    # re is imported here because it is only needed inside this function
    import re

    # convert transcript to lowercase so matching is case-insensitive
    text_lower = text.lower()

    # this will store counts for each category
    category_counts = {}

    # go through every algospeak term in the dictionary
    for term, meaning in algospeak_dict.items():
        # get the category for the current term
        category = get_category_fn(term)

        # if the category is not in the results yet, create a blank entry for it
        if category not in category_counts:
            category_counts[category] = {'count': 0, 'terms': []}

        # build a regex pattern with word boundaries
        # this avoids partial matches inside larger words
        pattern = r'\b' + re.escape(term.lower()) + r'\b'

        # count how many times the term appears in the transcript
        matches = len(re.findall(pattern, text_lower))

        # only update the results if the term appears at least once
        if matches > 0:
            category_counts[category]['count'] += matches
            category_counts[category]['terms'].append(term)

    return category_counts


def main():
    # get the root project folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # build the main paths used in this script
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dict_dir = os.path.join(base_dir, DICTIONARIES_DIR)

    # path to the sensitive words dictionary
    sensitive_words_path = os.path.join(dict_dir, 'sensitive_words.json')

    # path where the final csv file will be saved
    output_path = os.path.join(output_dir, 'category_analysis.csv')

    # load ad_status values from video_urls.csv so they can be matched back to each video
    import re as re_mod
    ad_status_lookup = {}
    input_csv_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')

    if os.path.exists(input_csv_path):
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '')

                # extract the YouTube video ID from either a standard or shortened URL
                match = re_mod.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)

                if match:
                    ad_status_lookup[match.group(1)] = row.get('ad_status', '')

    # load algospeak dictionary and category function
    algospeak_dict, get_category_fn = load_algospeak_dict()

    # make sure the sensitive words dictionary exists before continuing
    if not os.path.exists(sensitive_words_path):
        print(f"ERROR: Sensitive words dictionary not found: {sensitive_words_path}")
        sys.exit(1)

    # make sure step 2 has already created the raw data folder
    if not os.path.exists(raw_dir):
        print("ERROR: No raw data directory found. Run step 2 first.")
        sys.exit(1)

    # collect all video folders that contain a transcript.txt file
    video_ids = sorted([
        d for d in os.listdir(raw_dir)
        if os.path.isdir(os.path.join(raw_dir, d))
        and os.path.exists(os.path.join(raw_dir, d, 'transcript.txt'))
    ])

    # stop if no usable videos were found
    if not video_ids:
        print("ERROR: No extracted videos found")
        sys.exit(1)

    print("STEP 3b: CATEGORY CROSS-ANALYSIS")
    print(f"Videos: {len(video_ids)}\n")

    # create the output folder if it does not already exist
    os.makedirs(output_dir, exist_ok=True)

    # this list will hold the final results for each video
    results = []

    # these are the sensitive word categories we want to include as csv columns
    sensitive_categories = [
        'violence_death', 'sexual_content', 'profanity', 'drugs_substances',
        'hate_speech_slurs', 'mental_health', 'political_controversial',
        'weapons_military', 'coded_numbers'
    ]

    # go through each video one by one
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing: {video_id}")

        # load the transcript text
        transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()

        # skip videos with empty transcripts
        if not transcript:
            print("  SKIP: Empty transcript")
            continue

        # load metadata if available
        metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

        # count sensitive words by category
        sensitive_by_cat = analyze_transcript_by_category(transcript, sensitive_words_path)

        # count algospeak terms by category
        algospeak_by_cat = count_algospeak_by_category(transcript, algospeak_dict, get_category_fn)

        # start building the output row for this video
        result = {
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'channel_name': metadata.get('channel_name', ''),
            'ad_status': ad_status_lookup.get(video_id, ''),
        }

        # add sensitive-word category counts to the row
        total_sensitive = 0
        for cat in sensitive_categories:
            count = sensitive_by_cat.get(cat, {}).get('count', 0)
            result[f'sw_{cat}'] = count
            total_sensitive += count
        result['sw_total'] = total_sensitive

        # get all algospeak categories from the dictionary
        algospeak_categories = sorted(set(
            get_category_fn(term)
            for term in algospeak_dict.keys()
        ))

        # add algospeak category counts to the row
        total_algospeak = 0
        for cat in algospeak_categories:
            count = algospeak_by_cat.get(cat, {}).get('count', 0)
            result[f'as_{cat}'] = count
            total_algospeak += count
        result['as_total'] = total_algospeak

        # save this video's results
        results.append(result)

        print(f"  Sensitive: {total_sensitive} | Algospeak: {total_algospeak}")

    # save everything to a csv file
    if results:
        # use the keys from the first row as the csv column names
        fieldnames = list(results[0].keys())

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"\nSUCCESS: Category analysis complete")
        print(f"Results saved to: {output_path}")
        print(f"Videos analysed: {len(results)}")
    else:
        print("ERROR: No results to save")


if __name__ == "__main__":
    main()