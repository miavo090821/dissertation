# archive output

# main purpose:
# 1. keep a copy of the current generated files so previous runs are not lost
# 2. create a timestamped archive folder inside data/archive/
# 3. copy important pipeline folders such as output/ and raw/
# 4. also copy the input file video_urls.csv so the run is documented properly
# 5. optionally clear the old folders after archiving, so the next run starts fresh
# 6. when clearing, it also resets the ad_status column in video_urls.csv
# 7. includes an older legacy mode called --output-only, which only archives output/
#
# overall, this helps me keep each pipeline run organised and makes it easier
# to compare results across different runs without overwriting previous data

import sys
import os
import shutil
import argparse
import pandas as pd
from datetime import datetime

# add the project root folder into the Python path
# so the script can import config.py from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # import folder paths from the central config file
    # this keeps the script flexible and avoids hardcoding folder names here
    from config import DATA_OUTPUT_DIR, DATA_RAW_DIR, DATA_INPUT_DIR

except ImportError:
    # if config.py cannot be found, the script cannot continue
    print("ERROR: config.py not found!")
    sys.exit(1)


def archive_all(custom_name: str = None, clear_after: bool = True) -> str:
    
    """
    archive output/, raw/, and video_urls.csv into a timestamped folder.

    if clear_after is True, the original folders are emptied after the backup
    so the full pipeline can be re-run from scratch.

    returns:
        archive_path, archived_items
    or None if there is nothing to archive.
    """

    # get the base project directory
    # this is used to build absolute paths to all relevant folders
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # define the main folders/files that may need archiving
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")

    # check whether these folders/files actually exist and contain data
    # output and raw are only archived if they are not empty
    has_output = os.path.exists(output_dir) and any(os.scandir(output_dir))
    has_raw = os.path.exists(raw_dir) and any(os.scandir(raw_dir))
    has_input = os.path.exists(input_csv)

    # if there is no output and no raw data, then there is nothing meaningful to archive
    if not has_output and not has_raw:
        print("Nothing to archive: no output or raw data found")
        return None

    # create the main archive folder if it does not already exist
    archive_base = os.path.join(base_dir, 'data', 'archive')
    os.makedirs(archive_base, exist_ok=True)

    # create a unique archive folder name using the current date and time
    # this helps separate one pipeline run from another
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    archive_path = os.path.join(archive_base, archive_name)
    os.makedirs(archive_path, exist_ok=True)

    # keep track of what was archived so it can be printed later
    archived_items = []

    # archive the output folder if it exists and contains files
    if has_output:
        shutil.copytree(output_dir, os.path.join(archive_path, 'output'))
        archived_items.append('output/')

        # if requested, clear the output folder after backing it up
        # the charts folder is recreated because later pipeline steps may expect it
        if clear_after:
            shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)

    # archive the raw data folder if available
    if has_raw:
        shutil.copytree(raw_dir, os.path.join(archive_path, 'raw'))
        archived_items.append('raw/')

        # clear raw data folder if starting fresh is requested
        if clear_after:
            shutil.rmtree(raw_dir)
            os.makedirs(raw_dir, exist_ok=True)

    # archive the input CSV as well
    # this is useful because it preserves the state of the input file for that run
    if has_input:
        shutil.copy(input_csv, os.path.join(archive_path, 'video_urls.csv'))
        archived_items.append('video_urls.csv')

        if clear_after:
            # reset the ad_status column so the next run can start with fresh annotations
            # this is helpful when re-running the ad detection stage
            try:
                df = pd.read_csv(input_csv)
                if 'ad_status' in df.columns:
                    df['ad_status'] = ''
                    df.to_csv(input_csv, index=False)

            except Exception as e:
                # do not fully stop the script if this reset fails
                # just show a warning so the user knows what happened
                print(f"  Warning: Could not reset Ads column: {e}")

    return archive_path, archived_items


def archive_output(output_dir: str, custom_name: str = None) -> str:
    """
    legacy function that only archives the output directory

    this was the older behaviour before the script was extended
    to also archive raw data and the input CSV

    archive_all() should normally be used instead.
    """
    # if the folder does not exist, there is nothing to archive
    if not os.path.exists(output_dir):
        print(f"Nothing to archive: {output_dir} does not exist")
        return None

    # if the folder exists but is empty, there is also nothing to archive
    if not any(os.scandir(output_dir)):
        print(f"Nothing to archive: {output_dir} is empty")
        return None

    # create an archive folder beside the output folder
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)

    # create a timestamped archive name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    archive_path = os.path.join(archive_dir, archive_name)

    # copy the full output directory into the archive location
    shutil.copytree(output_dir, archive_path)

    return archive_path


def main():
    # define command-line arguments so the script can be run in different modes
    parser = argparse.ArgumentParser(description='Archive current output, raw data, and input CSV')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', default=True,
                        help='Clear output/raw after archiving (default: True)')
    parser.add_argument('--no-clear', action='store_true',
                        help='Do NOT clear output/raw after archiving')
    parser.add_argument('--output-only', action='store_true',
                        help='Only archive output directory (legacy behavior)')
    args = parser.parse_args()

    # by default the script clears after archiving
    # unless the user explicitly passes --no-clear
    clear_after = not args.no_clear

    print("=" * 60)
    print("  ARCHIVE DATA")
    print("=" * 60)

    if args.output_only:
        # legacy mode:
        # only back up the output folder, without archiving raw or input CSV
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)

        archive_path = archive_output(output_dir, args.name)

        if archive_path:
            print(f"\n✓ Archived output to: {archive_path}")

            # count how many files were archived for reporting
            file_count = sum(1 for _ in os.walk(archive_path) for _ in _[2])
            print(f"  Files archived: {file_count}")

            if clear_after:
                # remove all files from output after backup
                # keep the charts directory itself, but clear its contents
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

        # full archive mode:
        # back up output, raw data, and input CSV together
        result = archive_all(args.name, clear_after)

        if result:
            archive_path, archived_items = result
            print(f"\n✓ Archived to: {archive_path}")
            print(f"  Items archived: {', '.join(archived_items)}")

            # count total archived files across all copied folders
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