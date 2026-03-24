# step 3b: category cross-analysis
#
#1. this script compares sensitive word categories with algospeak categories for each video
#2. instead of just counting individual words, it groups them by topic (violence, drugs, etc.)
#3. the idea is that topic-level grouping shows which subjects correlate with demonetisation
#4. it pulls in both the sensitive words dictionary and the algospeak dictionary
#5. outputs a csv with per-category counts for both sensitive words and algospeak terms

import sys
import os
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR, DICTIONARIES_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

from scripts.utils.nlp_processor import (
    analyze_transcript_by_category,
    clean_and_lemmatize,
    count_sensitive_matches,
)


def load_algospeak_dict():
    # Load algospeak dictionary and category function.
    try:
        from scripts.utils.algospeak_dict import ALGOSPEAK_DICT, get_category
        return ALGOSPEAK_DICT, get_category
    except ImportError:
        print("WARNING: Could not import algospeak dictionary")
        return {}, lambda t: 'uncategorised'


def count_algospeak_by_category(text: str, algospeak_dict: dict, get_category_fn) -> dict:
    # count algospeak terms by category in text.
    import re
    text_lower = text.lower()
    category_counts = {}

    for term, meaning in algospeak_dict.items():
        category = get_category_fn(term)
        if category not in category_counts:
            category_counts[category] = {'count': 0, 'terms': []}

        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            category_counts[category]['count'] += matches
            category_counts[category]['terms'].append(term)

    return category_counts


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    dict_dir = os.path.join(base_dir, DICTIONARIES_DIR)

    sensitive_words_path = os.path.join(dict_dir, 'sensitive_words.json')
    output_path = os.path.join(output_dir, 'category_analysis.csv')

    # Load ad_status lookup
    import re as re_mod
    ad_status_lookup = {}
    input_csv_path = os.path.join(base_dir, DATA_INPUT_DIR, 'video_urls.csv')
    if os.path.exists(input_csv_path):
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '')
                match = re_mod.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
                if match:
                    ad_status_lookup[match.group(1)] = row.get('ad_status', '')

    # Load algospeak dictionary
    algospeak_dict, get_category_fn = load_algospeak_dict()

    # Check for sensitive words dictionary
    if not os.path.exists(sensitive_words_path):
        print(f"ERROR: Sensitive words dictionary not found: {sensitive_words_path}")
        sys.exit(1)

    # Check for extracted videos
    if not os.path.exists(raw_dir):
        print("ERROR: No raw data directory found. Run step 2 first.")
        sys.exit(1)

    video_ids = sorted([
        d for d in os.listdir(raw_dir)
        if os.path.isdir(os.path.join(raw_dir, d))
        and os.path.exists(os.path.join(raw_dir, d, 'transcript.txt'))
    ])

    if not video_ids:
        print("ERROR: No extracted videos found")
        sys.exit(1)

    print("STEP 3b: CATEGORY CROSS-ANALYSIS")
    print(f"Videos: {len(video_ids)}\n")

    os.makedirs(output_dir, exist_ok=True)
    results = []

    # Define category names for CSV columns
    sensitive_categories = [
        'violence_death', 'sexual_content', 'profanity', 'drugs_substances',
        'hate_speech_slurs', 'mental_health', 'political_controversial',
        'weapons_military', 'coded_numbers'
    ]

    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Analyzing: {video_id}")

        # Load transcript
        transcript_path = os.path.join(raw_dir, video_id, 'transcript.txt')
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()

        if not transcript:
            print("  SKIP: Empty transcript")
            continue

        # Load metadata
        metadata_path = os.path.join(raw_dir, video_id, 'metadata.json')
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

        # Per-category sensitive word counts
        sensitive_by_cat = analyze_transcript_by_category(transcript, sensitive_words_path)

        # Per-category algospeak counts
        algospeak_by_cat = count_algospeak_by_category(transcript, algospeak_dict, get_category_fn)

        # Build result row
        result = {
            'video_id': video_id,
            'title': metadata.get('title', ''),
            'channel_name': metadata.get('channel_name', ''),
            'ad_status': ad_status_lookup.get(video_id, ''),
        }

        # Add sensitive word category counts
        total_sensitive = 0
        for cat in sensitive_categories:
            count = sensitive_by_cat.get(cat, {}).get('count', 0)
            result[f'sw_{cat}'] = count
            total_sensitive += count
        result['sw_total'] = total_sensitive

        # Add algospeak category counts
        algospeak_categories = sorted(set(
            get_category_fn(term)
            for term in algospeak_dict.keys()
        ))
        total_algospeak = 0
        for cat in algospeak_categories:
            count = algospeak_by_cat.get(cat, {}).get('count', 0)
            result[f'as_{cat}'] = count
            total_algospeak += count
        result['as_total'] = total_algospeak

        results.append(result)
        print(f"  Sensitive: {total_sensitive} | Algospeak: {total_algospeak}")

    # Save results
    if results:
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
