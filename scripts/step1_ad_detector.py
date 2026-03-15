"""
Ad Detection Module for YouTube Self-Censorship Research
=========================================================

Detects advertisements on YouTube videos using stealth browser automation
and UI-based detection (checking for "Sponsored" label in video player).

Methodology:
- Uses headed browser with stealth settings to avoid bot detection
- Checks for "Sponsored" label which only appears when an ad is actually rendered
- This approach detects ad DELIVERY, not just ad INFRASTRUCTURE

Note: DOM variables (adTimeOffset, playerAds) and Network signals (ad_break, pagead)
were evaluated but removed as they indicate infrastructure availability, not actual
ad delivery, producing false positives on non-monetised content.

Reference: YouTube Self-Censorship Research Project (RQ1 Methodology)
"""

# Standard library imports
import argparse
import asyncio
import os
import re
import sys

# Third-party imports
import pandas as pd

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project configuration paths
try:
    from config import DATA_INPUT_DIR, DATA_OUTPUT_DIR, AD_DETECTION_FILE
except ImportError:
    # Fallback defaults if config not available (e.g., standalone testing)
    DATA_INPUT_DIR = "data/input"
    DATA_OUTPUT_DIR = "data/output"
    AD_DETECTION_FILE = "ad_detection_results.csv"

# Import detection engine classes
from scripts.utils.ad_detection_engine import (
    UIAdDetectionResult,
    AdDetectionResult,
    AdDetector,
    detect_ads_sync,
)


# Extract the 11-character video ID from a YouTube URL
def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url


RECHECK_COLUMNS = ['recheck_round_1', 'recheck_round_2', 'recheck_round_3',
                    'recheck_round_4', 'recheck_round_5']

#  this is for the 5th times on "No-ad videos". so the pipeline compiles 
# all the video fresh starts, if any video has yes ad, then pass, if it shows 'no' ad
# then this function will run the ad detection 5 times to double check whether it's correct. 
def _ensure_recheck_columns(df):
    """Add recheck_round_1..5 columns if they don't exist."""
    for col in RECHECK_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''
    return df


def _needs_recheck(row):
    """True if ad_status=No but recheck_round_1 is empty (unverified No)."""
    ad = str(row.get('ad_status', '')).strip().lower()
    r1 = str(row.get('recheck_round_1', '')).strip()
    return ad == 'no' and r1 in ('', 'nan')


def _needs_full_detect(row):
    """True if ad_status is empty (not yet processed)."""
    ad = str(row.get('ad_status', '')).strip().lower()
    return ad not in ('yes', 'no')


def _is_complete(row):
    """True if video is fully processed (Yes, or No with rechecks filled)."""
    ad = str(row.get('ad_status', '')).strip().lower()
    if ad == 'yes':
        return True
    if ad == 'no':
        r1 = str(row.get('recheck_round_1', '')).strip()
        return r1 not in ('', 'nan')
    return False


# Batch ad detection with integrated recheck flow
def main():
    # Get base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Resolve paths
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, AD_DETECTION_FILE)

    # Check input exists
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Detect ads on YouTube videos')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip fully processed videos, resume unverified Nos and new videos')
    parser.add_argument('--recheck-no', action='store_true',
                        help='Manual mode: re-check only videos where ad_status is No')
    args = parser.parse_args()

    # Read video URLs
    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    df = _ensure_recheck_columns(df)

    # Build processing queue with priority ordering
    # Each entry: (index, video_id, mode) where mode is 'recheck_only' or 'full'
    queue = []

    if args.recheck_no:
        # Legacy manual mode: recheck all No videos
        for i, row in df.iterrows():
            if str(row.get('ad_status', '')).strip().lower() == 'no':
                queue.append((i, extract_video_id(row['url']), 'recheck_only'))
    else:
        # Priority 1: Unverified "No" videos (ad_status=No, recheck_round_1 empty)
        for i, row in df.iterrows():
            if _needs_recheck(row):
                queue.append((i, extract_video_id(row['url']), 'recheck_only'))

        # Priority 2: New videos (ad_status empty)
        for i, row in df.iterrows():
            if _needs_full_detect(row):
                queue.append((i, extract_video_id(row['url']), 'full'))

        if args.skip_existing:
            # skip-existing: only process the queue above (skip completed videos)
            pass
        else:
            # Without skip-existing: also re-process completed videos fully
            for i, row in df.iterrows():
                if _is_complete(row):
                    queue.append((i, extract_video_id(row['url']), 'full'))

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

    if not queue:
        print("All videos already processed. Nothing to do.")
        return

    # Run integrated detection + recheck flow
    print("\nStarting ad detection...")
    print("NOTE: This requires a visible browser window. Ads cannot be detected in headless mode.")
    print()

    all_results = []

    async def run_detection():
        detector = AdDetector(headless=False)
        await detector.setup()

        try:
            for q_idx, (df_idx, video_id, mode) in enumerate(queue):
                print(f"\n[{q_idx+1}/{len(queue)}] {video_id} ({mode})")

                if mode == 'full':
                    # Step 1: Initial detection
                    result = await detector.detect(video_id)
                    verdict = "Yes" if result.verdict else "No"
                    print(f"  Initial detect: {verdict}")

                    if result.verdict:
                        # Yes on first detect — write and move on
                        df.at[df_idx, 'ad_status'] = 'Yes'
                        # Leave recheck columns empty
                        for col in RECHECK_COLUMNS:
                            df.at[df_idx, col] = ''
                        all_results.append(result)
                        df.to_csv(input_csv, index=False)
                        print(f"  -> Saved (Yes, no recheck needed)")

                        # Restart browser periodically
                        if (q_idx + 1) % 5 == 0 and q_idx < len(queue) - 1:
                            print("  Restarting browser...")
                            await detector.cleanup()
                            await detector.setup()
                        continue

                    # No on first detect — fall through to recheck
                    df.at[df_idx, 'ad_status'] = 'No'

                # Recheck: 5 rounds
                print(f"  Running 5 recheck rounds...")
                flipped = False
                for round_num in range(1, 6):
                    col = f'recheck_round_{round_num}'
                    result = await detector.detect(video_id)
                    round_verdict = "Yes" if result.verdict else "No"
                    df.at[df_idx, col] = round_verdict
                    print(f"  Round {round_num}/5: {round_verdict}")

                    if result.verdict:
                        # Flip ad_status to Yes, leave remaining columns empty
                        df.at[df_idx, 'ad_status'] = 'Yes'
                        flipped = True
                        all_results.append(result)
                        df.to_csv(input_csv, index=False)
                        print(f"  -> Flipped to Yes on round {round_num}, saved")
                        break

                if not flipped:
                    # All 5 rounds said No — confirmed
                    all_results.append(result)
                    df.to_csv(input_csv, index=False)
                    print(f"  -> Confirmed No after 5 recheck rounds, saved")

                # Restart browser periodically
                if (q_idx + 1) % 5 == 0 and q_idx < len(queue) - 1:
                    print("  Restarting browser...")
                    await detector.cleanup()
                    await detector.setup()

        finally:
            await detector.cleanup()

    asyncio.run(run_detection())

    # Save detailed results to output
    if all_results:
        detailed_data = [r.to_dict() for r in all_results]
        detailed_df = pd.DataFrame(detailed_data)
        detailed_df.to_csv(output_csv, index=False)
        print(f"\nSaved detailed results to {output_csv}")

    # Print summary
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
    # Single video mode: pass a video ID as argument (not a flag)
    if len(sys.argv) == 2 and not sys.argv[1].startswith('--'):
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
        # Batch processing on video_urls.csv (supports --recheck-no flag)
        main()
