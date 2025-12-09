# Archives the current output folder before re-running analysis.
# Creates timestamped backup in data/archive/.
import sys
import os
import shutil
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def archive_output(output_dir: str, custom_name: str = None) -> str:
    # Archive existing output folder with timestamp.
    
    # Args:
    #     output_dir: Path to output directory
    #     custom_name: Optional custom suffix for archive name
        
    # Returns:
    #     Path to archived folder or None if nothing to archive
    if not os.path.exists(output_dir):
        print(f"Nothing to archive: {output_dir} does not exist")
        return None
    
    # Check if output has any files
    if not any(os.scandir(output_dir)):
        print(f"Nothing to archive: {output_dir} is empty")
        return None
    
    # Create archive directory
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    
    # Generate archive name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'
    
    archive_path = os.path.join(archive_dir, archive_name)
    
    # Copy output to archive
    shutil.copytree(output_dir, archive_path)
    
    return archive_path

def main():
    parser = argparse.ArgumentParser(description='Archive current output folder')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', help='Clear output after archiving')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    
    print("=" * 60)
    print("  ARCHIVE OUTPUT")
    print("=" * 60)
    
    archive_path = archive_output(output_dir, args.name)
    
    if archive_path:
        print(f"\n✓ Archived to: {archive_path}")
        
        # List archived files
        file_count = sum(1 for _ in os.walk(archive_path) for _ in _[2])
        print(f"  Files archived: {file_count}")
        
        if args.clear:
            print("\nOutput directory cleared for new analysis.")
    else:
        print("\nNothing to archive.")
    
if __name__ == "__main__":
    main()