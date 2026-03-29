# step 1: ad detection (stealth/ui method)
# 
# this script is the first step of my pipeline and is responsible for checking
# whether a YouTube video is showing ads or not.
#
# what this script does:
# 1. opens YouTube videos in a real browser using stealth settings
# 2. checks for visible ad-related UI elements such as the "Sponsored" label
# 3. uses the actual rendered player interface instead of only relying on DOM or network requests
# 4. saves the final ad decision back into video_urls.csv
# 5. also saves a more detailed CSV file in the output folder for later analysis
#
# why I used this method:
# - I wanted to detect real ad delivery, meaning ads that actually appear to the viewer
# - I tested DOM variables such as adTimeOffset and playerAds, and network signals such as
#   ad_break and pagead, but they sometimes suggested ads were present even when no ad was shown
# - because of that, I chose the UI/stealth approach as the main method in this stage
#
# reliability step:
# - if a video is first classified as having no ads, the script checks it 5 more times
# - this is because ad delivery can be inconsistent, so one failed detection is not enough
#   to confidently say that a video has no ads


#  i use LLMs to help me write more comments to help the readabilities but the main 
# ideas and methods are written by me

# argparse is used to read command-line options such as --skip-existing or --recheck-no
# this makes the script more flexible because I can run it in different modes
import argparse

# asyncio is used because the ad detection process runs with async browser functions
# this helps manage the browser workflow properly when calling async setup/detect/cleanup methods
import asyncio

# os is used for file and folder handling, for example joining paths and checking whether files exist
import os

# re is Python's regular expression module
# I use it here to extract the YouTube video ID from different URL formats
import re

# sys is used for system-level operations such as exiting the script
# it is also used to modify the Python path so the script can import files from the project root
import sys

# pandas is used to read, edit, and save CSV files such as video_urls.csv
# this is important because the script updates ad_status and recheck results directly in the dataset
import pandas as pd

# add the project root directory to the Python path
# this allows the script to import config.py and utility files from the main project folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import folder and file settings from config.py
    # this makes the script easier to maintain because paths are controlled centrally
    from config import DATA_INPUT_DIR, DATA_OUTPUT_DIR, AD_DETECTION_FILE
except ImportError:
    # fallback values in case the script is run on its own without config.py
    # this helps the file still work in a more standalone way
    DATA_INPUT_DIR = "data/input"
    DATA_OUTPUT_DIR = "data/output"
    AD_DETECTION_FILE = "ad_detection_results.csv"

# import the ad detection classes and helper function
# the main detection logic is implemented in the ad_detection_engine file
from scripts.utils.ad_detection_engine import (
    UIAdDetectionResult,
    AdDetectionResult,
    AdDetector,
    detect_ads_sync,
)


# this function extracts the 11-character YouTube video ID from different URL formats
# for example, it can handle watch URLs, short youtu.be URLs, embed URLs, or just a raw ID
def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # if no pattern matches, return the original input
    # this avoids crashing and lets later logic deal with it if needed
    return url


# these columns store the results of the 5 extra recheck rounds
# they are mainly used when a video is initially classified as "No"
RECHECK_COLUMNS = ['recheck_round_1', 'recheck_round_2', 'recheck_round_3',
                    'recheck_round_4', 'recheck_round_5']


# this function makes sure the dataframe has all the columns needed for rechecking
# I added this so the pipeline will not fail if the CSV is missing some of these columns
def _ensure_recheck_columns(df):
    """adds recheck_round_1..5 columns if they don't exist yet."""
    for col in RECHECK_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    # also make sure the main ad_status column exists
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''
    return df


# this checks whether a row needs the 5-round recheck process
# a video needs recheck if ad_status is already "No" but the recheck columns have not been filled yet
def _needs_recheck(row):
    """true if ad_status=No but we haven't done the recheck rounds yet."""
    ad = str(row.get('ad_status', '')).strip().lower()
    r1 = str(row.get('recheck_round_1', '')).strip()
    return ad == 'no' and r1 in ('', 'nan')


# this checks whether a video has never been processed at all
# in other words, if ad_status is still blank or contains something unexpected
def _needs_full_detect(row):
    """true if this video hasn't been processed at all (no ad_status)."""
    ad = str(row.get('ad_status', '')).strip().lower()
    return ad not in ('yes', 'no')


# this checks whether the row is already fully complete
# complete means either:
# - it has a final "Yes", or
# - it has a final "No" and the recheck stage was already done
def _is_complete(row):
    """true if video is done - either Yes, or No with rechecks filled in."""
    ad = str(row.get('ad_status', '')).strip().lower()
    if ad == 'yes':
        return True
    if ad == 'no':
        r1 = str(row.get('recheck_round_1', '')).strip()
        return r1 not in ('', 'nan')
    return False


# main function for batch ad detection
# this is the part that reads the CSV, builds the processing queue,
# runs the browser detection, and saves the results
def main():
    # define the base project directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # build the important input/output paths
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, AD_DETECTION_FILE)

    # stop early if the input CSV does not exist
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # create the output directory if it does not already exist
    os.makedirs(output_dir, exist_ok=True)

    # define optional command-line arguments
    # these flags allow the script to run in different modes depending on what stage I need
    parser = argparse.ArgumentParser(description='Detect ads on YouTube videos')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip fully processed videos, resume unverified Nos and new videos')
    parser.add_argument('--recheck-no', action='store_true',
                        help='Manual mode: re-check only videos where ad_status is No')
    args = parser.parse_args()

    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    # make sure the CSV contains the expected url column
    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    # ensure all recheck-related columns are present before processing
    df = _ensure_recheck_columns(df)

    # build the processing queue
    # I designed the queue so that unfinished "No" cases are prioritised first,
    # because these are the uncertain ones that need confirmation
    queue = []

    if args.recheck_no:
        # manual mode:
        # only recheck videos that currently have ad_status = No
        for i, row in df.iterrows():
            if str(row.get('ad_status', '')).strip().lower() == 'no':
                queue.append((i, extract_video_id(row['url']), 'recheck_only'))
    else:
        # first priority:
        # videos that were marked "No" before, but have not yet gone through recheck rounds
        for i, row in df.iterrows():
            if _needs_recheck(row):
                queue.append((i, extract_video_id(row['url']), 'recheck_only'))

        # second priority:
        # completely new videos that have never been processed yet
        for i, row in df.iterrows():
            if _needs_full_detect(row):
                queue.append((i, extract_video_id(row['url']), 'full'))

        if args.skip_existing:
            # if skip-existing is used, leave completed rows out of the queue
            pass
        else:
            # otherwise, also reprocess completed videos
            # this can be useful if I want to rerun the full batch from the beginning
            for i, row in df.iterrows():
                if _is_complete(row):
                    queue.append((i, extract_video_id(row['url']), 'full'))

    # count how many videos fall into each category
    recheck_count = sum(1 for _, _, m in queue if m == 'recheck_only')
    full_count = sum(1 for _, _, m in queue if m == 'full')
    skipped = len(df) - len(queue)

    print(f"Found {len(df)} total videos")
    if recheck_count > 0:
        print(f"  Unverified No videos to recheck: {recheck_count}")
    if full_count > 0:
        print(f"  Videos needing full detection: {full_count}")
    if skipped > 0:
        print(f"  Skipping: {skipped}")
    print(f"Processing {len(queue)} videos total")

    # if the queue is empty, everything has already been done
    if not queue:
        print("All videos already processed. Nothing to do.")
        return

    print("\nStarting ad detection...")
    print("NOTE: This requires a visible browser window. Ads cannot be detected in headless mode.")
    print()

    # this list stores detailed result objects so they can later be written to the output CSV
    all_results = []

    async def run_detection():
        # create the detector using a visible browser
        # I set headless=False because the UI elements must actually render to be detected
        detector = AdDetector(headless=False)
        await detector.setup()

        try:
            # loop through each queued video one by one
            for q_idx, (df_idx, video_id, mode) in enumerate(queue):
                print(f"\n[{q_idx+1}/{len(queue)}] {video_id} ({mode})")

                if mode == 'full':
                    # first run the initial detection
                    result = await detector.detect(video_id)
                    verdict = "Yes" if result.verdict else "No"
                    print(f"  Initial detect: {verdict}")

                    if result.verdict:
                        # if ads are found immediately, I treat that as enough evidence
                        # there is no need to recheck a positive ad detection
                        df.at[df_idx, 'ad_status'] = 'Yes'
                        for col in RECHECK_COLUMNS:
                            df.at[df_idx, col] = ''
                        all_results.append(result)
                        df.to_csv(input_csv, index=False)
                        print(f"  -> Saved (Yes, no recheck needed)")

                        # restart browser every 5 videos to reduce browser fingerprint build-up
                        # this was added to make the detection process more stable over time
                        if (q_idx + 1) % 5 == 0 and q_idx < len(queue) - 1:
                            print("  Restarting browser...")
                            await detector.cleanup()
                            await detector.setup()
                        continue

                    # if the first check says no ads, store No for now
                    # but do not trust it fully yet because No results are less certain
                    df.at[df_idx, 'ad_status'] = 'No'

                # if we reach here, the video needs rechecking
                # this happens either because it was already a No case, or because
                # the full detection just returned No
                print(f"  Running 5 recheck rounds...")
                flipped = False

                for round_num in range(1, 6):
                    col = f'recheck_round_{round_num}'
                    result = await detector.detect(video_id)
                    round_verdict = "Yes" if result.verdict else "No"
                    df.at[df_idx, col] = round_verdict
                    print(f"  Round {round_num}/5: {round_verdict}")

                    if result.verdict:
                        # if any recheck round finds ads, I flip the final status to Yes
                        # this is because one confirmed ad render is enough to classify the video as having ads
                        df.at[df_idx, 'ad_status'] = 'Yes'
                        flipped = True
                        all_results.append(result)
                        df.to_csv(input_csv, index=False)
                        print(f"  -> Flipped to Yes on round {round_num}, saved")
                        break

                if not flipped:
                    # if all 5 rechecks still show no ads, then I keep the final label as No
                    # this gives more confidence that the video genuinely had no ads shown
                    all_results.append(result)
                    df.to_csv(input_csv, index=False)
                    print(f"  -> Confirmed No after 5 recheck rounds, saved")

                # restart the browser after every 5 processed videos
                # again, this is to reduce issues from repeated automated browsing
                if (q_idx + 1) % 5 == 0 and q_idx < len(queue) - 1:
                    print("  Restarting browser...")
                    await detector.cleanup()
                    await detector.setup()

        finally:
            # make sure the browser is always closed properly
            # even if the script stops because of an error
            await detector.cleanup()

    # run the async detection loop
    asyncio.run(run_detection())

    # save the detailed per-video results to the output directory
    # this file is useful for debugging and also for later reporting/analysis
    if all_results:
        detailed_data = [r.to_dict() for r in all_results]
        detailed_df = pd.DataFrame(detailed_data)
        detailed_df.to_csv(output_csv, index=False)
        print(f"\nSaved detailed results to {output_csv}")

    # basic summary statistics for the terminal output
    yes_count = sum(1 for r in all_results if r.verdict)
    no_count = len(all_results) - yes_count
    error_count = sum(1 for r in all_results if r.error)

    print(f"\n{'='*40}")
    print("SUMMARY")
    print(f"{'='*40}")
    print(f"Videos processed: {len(all_results)}")
    print(f"With ads:         {yes_count}")
    print(f"Without ads:      {no_count}")
    if error_count:
        print(f"Errors:           {error_count}")


if __name__ == "__main__":
    # this section allows the script to be used in two ways:
    # 1. batch mode -> process the CSV file
    # 2. single video mode -> pass one video ID directly in the terminal
    if len(sys.argv) == 2 and not sys.argv[1].startswith('--'):
        # single video mode is useful for quick testing or debugging
        video_id = sys.argv[1]
        print(f"Detecting ads for video: {video_id}")
        print("(This requires a visible browser window)")
        print()

        result = detect_ads_sync(video_id, headless=False)

        print("\n=== Detection Results ===")
        print(f"Video ID: {result.video_id}")
        print(f"\nUI Detection:")
        print(f"  Sponsored label: {result.ui_result.sponsored_label}")
        print(f"  Ad label: {result.ui_result.ad_label}")
        print(f"  Skip button: {result.ui_result.skip_button}")
        print(f"  Ad countdown: {result.ui_result.ad_countdown}")
        print(f"  Ad overlay: {result.ui_result.ad_overlay}")
        print(f"  Ad-showing class: {result.ui_result.ad_showing_class}")
        print(f"\nVerdict: {'Has Ads' if result.verdict else 'No Ads'}")
        print(f"Confidence: {result.confidence}")
        if result.error:
            print(f"Error: {result.error}")
    else:
        # default mode is batch processing using the input CSV
        main()