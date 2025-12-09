# Archives the current output folder before re-running analysis.
# Creates timestamped backup in data/archive/.
import sys
import os
import shutil
import argparse
from datetime import datetime

# Add project root directory to Python path so config can be imported reliably
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Attempt to import output directory path from config file
try:
    from config import DATA_OUTPUT_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

# Function to archive the current output folder into a timestamped directory
def archive_output(output_dir: str, custom_name: str = None) -> str:
    # Return early if the output directory does not exist
    if not os.path.exists(output_dir):
        print(f"Nothing to archive: {output_dir} does not exist")
        return None
    
    # Return early if the directory exists but is empty
    if not any(os.scandir(output_dir)):
        print(f"Nothing to archive: {output_dir} is empty")
        return None
    
    # Create an archive directory next to the output directory if not already present
    archive_dir = os.path.join(os.path.dirname(output_dir), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    
    # Create a timestamp for naming the archive
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # If a custom name is provided, include it in the archive folder name
    if custom_name:
        archive_name = f'run_{timestamp}_{custom_name}'
    else:
        archive_name = f'run_{timestamp}'
    
    # Full path where the archived output will be stored
    archive_path = os.path.join(archive_dir, archive_name)
    
    # Copy the entire output directory into the archive folder
    shutil.copytree(output_dir, archive_path)
    
    # Return the path of the newly created archive
    return archive_path

# Main script entry point
def main():
    # Parse command line arguments for custom archive name and clearing behaviour
    parser = argparse.ArgumentParser(description='Archive current output folder')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', help='Clear output after archiving')
    args = parser.parse_args()
    
    # Compute the absolute path to the output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    
    # Display section header
    print("=" * 60)
    print("  ARCHIVE OUTPUT")
    print("=" * 60)
    
    # Execute archiving operation
    archive_path = archive_output(output_dir, args.name)
    
    # If an archive was created, print success information
    if archive_path:
        print(f"\n✓ Archived to: {archive_path}")
        
        # Count total number of files stored in the archive
        file_count = sum(1 for _ in os.walk(archive_path) for _ in _[2])
        print(f"  Files archived: {file_count}")
        
        # If user selected the clear flag, remove contents of output directory safely
        if args.clear:
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                
                # Remove regular files directly
                if os.path.isfile(item_path):
                    os.remove(item_path)
                
                # If directory is charts, keep folder but empty its contents
                elif item == 'charts':
                    for chart in os.listdir(item_path):
                        os.remove(os.path.join(item_path, chart))
            
            print("✓ Cleared output directory")
        
        # Indicate that processing steps can be safely rerun
        print("\nYou can now re-run analysis steps 3-7.")
    
    # Branch for when nothing could be archived
    else:
        print("\nNothing to archive.")

# Ensure this script runs only when executed directly
if __name__ == "__main__":
    main()
