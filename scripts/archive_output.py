# Archives the current output, raw data, and input CSV before re-running analysis.
# Creates timestamped backup in data/archive/, then clears originals.
import sys
import os
import shutil
import argparse
import pandas as pd
from datetime import datetime

# Ensure the project root directory is added to Python path so config can be imported correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing directory paths from config
try:
    from config import DATA_OUTPUT_DIR, DATA_RAW_DIR, DATA_INPUT_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)


def archive_all(custom_name: str = None, clear_after: bool = True) -> str:
    """
    Archive all generated data and optionally clear originals.

    Archives:
    - data/output/ (analysis results, charts)
    - data/raw/ (extracted video data)
    - data/input/video_urls.csv (with ad detection results)

    Args:
        custom_name: Optional suffix for archive folder name
        clear_after: If True, delete originals after archiving (default True)

    Returns:
        Path to archive folder, or None if nothing to archive
    """
    # Get base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Resolve full paths
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    raw_dir = os.path.join(base_dir, DATA_RAW_DIR)
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")

    # Check if there's anything to archive
    has_output = os.path.exists(output_dir) and any(os.scandir(output_dir))
    has_raw = os.path.exists(raw_dir) and any(os.scandir(raw_dir))
    has_input = os.path.exists(input_csv)

    if not has_output and not has_raw:
        print("Nothing to archive: no output or raw data found")
        return None

    # Create archive directory
    archive_base = os.path.join(base_dir, 'data', 'archive')
    os.makedirs(archive_base, exist_ok=True)

    # Create timestamped archive folder
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    archive_path = os.path.join(archive_base, archive_name)
    os.makedirs(archive_path, exist_ok=True)

    archived_items = []

    # Archive output directory
    if has_output:
        shutil.copytree(output_dir, os.path.join(archive_path, 'output'))
        archived_items.append('output/')

        if clear_after:
            shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            # Recreate charts subdirectory
            os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)

    # Archive raw directory
    if has_raw:
        shutil.copytree(raw_dir, os.path.join(archive_path, 'raw'))
        archived_items.append('raw/')

        if clear_after:
            shutil.rmtree(raw_dir)
            os.makedirs(raw_dir, exist_ok=True)

    # Archive and reset video_urls.csv
    if has_input:
        # Copy to archive
        shutil.copy(input_csv, os.path.join(archive_path, 'video_urls.csv'))
        archived_items.append('video_urls.csv')

        if clear_after:
            # Reset the Ads column to empty in original
            try:
                df = pd.read_csv(input_csv)
                if 'ad_status' in df.columns:
                    df['ad_status'] = ''
                    df.to_csv(input_csv, index=False)
            except Exception as e:
                print(f"  Warning: Could not reset Ads column: {e}")

    return archive_path, archived_items


# Legacy function for backwards compatibility
def archive_output(output_dir: str, custom_name: str = None) -> str:
    """
    Archive just the output directory (legacy behavior).

    For full archiving including raw data and input CSV, use archive_all().
    """
    # Return early if output directory does not exist
    if not os.path.exists(output_dir):
        print(f"Nothing to archive: {output_dir} does not exist")
        return None

    # Return early if directory exists but contains no files or folders
    if not any(os.scandir(output_dir)):
        print(f"Nothing to archive: {output_dir} is empty")
        return None

    # Create archive directory alongside the output directory
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)

    # Create a timestamp to ensure unique archive folder names
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Use custom suffix if provided
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'

    # Full path of archive folder
    archive_path = os.path.join(archive_dir, archive_name)

    # Copy the entire output directory into the archive folder
    shutil.copytree(output_dir, archive_path)

    # Return the location of the archived output
    return archive_path


# Main function to handle command line execution
def main():
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Archive current output, raw data, and input CSV')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', default=True,
                        help='Clear output/raw after archiving (default: True)')
    parser.add_argument('--no-clear', action='store_true',
                        help='Do NOT clear output/raw after archiving')
    parser.add_argument('--output-only', action='store_true',
                        help='Only archive output directory (legacy behavior)')
    args = parser.parse_args()

    # Determine whether to clear after archiving
    clear_after = not args.no_clear

    # Display header text for clarity
    print("=" * 60)
    print("  ARCHIVE DATA")
    print("=" * 60)

    if args.output_only:
        # Legacy behavior: only archive output
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
        # New behavior: archive all data
        result = archive_all(args.name, clear_after)

        if result:
            archive_path, archived_items = result
            print(f"\n✓ Archived to: {archive_path}")
            print(f"  Items archived: {', '.join(archived_items)}")

            # Count total files
            file_count = sum(1 for root, dirs, files in os.walk(archive_path) for f in files)
            print(f"  Total files: {file_count}")

            if clear_after:
                print("✓ Cleared original directories")
                print("✓ Reset Ads column in video_urls.csv")

            print("\nYou can now re-run the full pipeline with python main.py")
        else:
            print("\nNothing to archive.")


# Ensure the main function runs only when script is executed directly
if __name__ == "__main__":
    main()
