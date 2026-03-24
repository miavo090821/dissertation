# archive output
#
#1. this script backs up all generated data before re-running the analysis pipeline
#2. creates a timestamped folder in data/archive/ and copies output, raw data, and input csv
#3. optionally clears the originals after archiving so you start fresh
#4. has a legacy --output-only mode that just archives the output folder
#5. also resets the ad_status column in video_urls.csv when clearing

import sys
import os
import shutil
import argparse
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_OUTPUT_DIR, DATA_RAW_DIR, DATA_INPUT_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)


def archive_all(custom_name: str = None, clear_after: bool = True) -> str:
    """archives output/, raw/, and video_urls.csv into a timestamped folder.
    if clear_after is true it wipes the originals so you can re-run from scratch.
    returns the archive path and list of what got archived, or none if nothing to do."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")

    has_output = os.path.exists(output_dir) and any(os.scandir(output_dir))
    has_raw = os.path.exists(raw_dir) and any(os.scandir(raw_dir))
    has_input = os.path.exists(input_csv)

    if not has_output and not has_raw:
        print("Nothing to archive: no output or raw data found")
        return None

    archive_base = os.path.join(base_dir, 'data', 'archive')
    os.makedirs(archive_base, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    archive_path = os.path.join(archive_base, archive_name)
    os.makedirs(archive_path, exist_ok=True)

    archived_items = []

    if has_output:
        shutil.copytree(output_dir, os.path.join(archive_path, 'output'))
        archived_items.append('output/')

        if clear_after:
            shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)

    if has_raw:
        shutil.copytree(raw_dir, os.path.join(archive_path, 'raw'))
        archived_items.append('raw/')

        if clear_after:
            shutil.rmtree(raw_dir)
            os.makedirs(raw_dir, exist_ok=True)

    if has_input:
        shutil.copy(input_csv, os.path.join(archive_path, 'video_urls.csv'))
        archived_items.append('video_urls.csv')

        if clear_after:
            # blank out the ad_status column so its ready for fresh annotation
            try:
                df = pd.read_csv(input_csv)
                if 'ad_status' in df.columns:
                    df['ad_status'] = ''
                    df.to_csv(input_csv, index=False)
            except Exception as e:
                print(f"  Warning: Could not reset Ads column: {e}")

    return archive_path, archived_items


def archive_output(output_dir: str, custom_name: str = None) -> str:
    """legacy function - just archives the output directory on its own.
    use archive_all() instead if you want to backup everything."""
    if not os.path.exists(output_dir):
        print(f"Nothing to archive: {output_dir} does not exist")
        return None

    if not any(os.scandir(output_dir)):
        print(f"Nothing to archive: {output_dir} is empty")
        return None

    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    archive_path = os.path.join(archive_dir, archive_name)

    shutil.copytree(output_dir, archive_path)

    return archive_path


def main():
    parser = argparse.ArgumentParser(description='Archive current output, raw data, and input CSV')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', default=True,
                        help='Clear output/raw after archiving (default: True)')
    parser.add_argument('--no-clear', action='store_true',
                        help='Do NOT clear output/raw after archiving')
    parser.add_argument('--output-only', action='store_true',
                        help='Only archive output directory (legacy behavior)')
    args = parser.parse_args()

    clear_after = not args.no_clear

    print("=" * 60)
    print("  ARCHIVE DATA")
    print("=" * 60)

    if args.output_only:
        # legacy mode: only backup the output folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)

        archive_path = archive_output(output_dir, args.name)

        if archive_path:
            print(f"\n✓ Archived output to: {archive_path}")
            file_count = sum(1 for _ in os.walk(archive_path) for _ in _[2])
            print(f"  Files archived: {file_count}")

            if clear_after:
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path) and item != 'charts':
                        shutil.rmtree(item_path)
                    elif item == 'charts':
                        for chart in os.listdir(item_path):
                            os.remove(os.path.join(item_path, chart))
                print("✓ Cleared output directory")
        else:
            print("\nNothing to archive.")
    else:
        # full archive mode: backup output, raw, and input csv
        result = archive_all(args.name, clear_after)

        if result:
            archive_path, archived_items = result
            print(f"\n✓ Archived to: {archive_path}")
            print(f"  Items archived: {', '.join(archived_items)}")

            file_count = sum(1 for root, dirs, files in os.walk(archive_path) for f in files)
            print(f"  Total files: {file_count}")

            if clear_after:
                print("✓ Cleared original directories")
                print("✓ Reset Ads column in video_urls.csv")

            print("\nYou can now re-run the full pipeline with python main.py")
        else:
            print("\nNothing to archive.")


if __name__ == "__main__":
    main()
