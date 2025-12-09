# Archives the current output folder before re-running analysis.
# Creates timestamped backup in data/archive/.
import sys
import os
import shutil
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def archive_output(output_dir: str, custom_name: str = None) -> str:
    # Archive the existing output directory by moving it to an archive folder with a timestamp.
    
    # Args:
    #     output_dir: Path to the current output directory.
    #     custom_name: Optional custom name to include in the archive folder name.
        
    # Returns:
    #     The path to the newly created archive directory.
    if not os.path.exists(output_dir):
        print("No existing output directory to archive.")
        return ""
    
    # Create archive directory if it doesn't exist
    archive_base_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_base_dir, exist_ok=True)
    
    # Create timestamped archive folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_folder_name = f"output_archive_{timestamp}"
    if custom_name:
        archive_folder_name += f"_{custom_name}"
    
    archive_dir = os.path.join(archive_base_dir, archive_folder_name)
    
    # Move the existing output directory to the archive location
    shutil.move(output_dir, archive_dir)
    print(f"Archived existing output to: {archive_dir}")
    
    return archive_dir


def main():
    parser = argparse.ArgumentParser(description="Archive existing output directory.")
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Path to the output directory to archive.'
    )
    parser.add_argument(
        '--custom_name',
        type=str,
        default=None,
        help='Optional custom name to include in the archive folder name.'
    )
    args = parser.parse_args()
    
    archive_output(args.output_dir, args.custom_name)
    
if __name__ == "__main__":
    main()