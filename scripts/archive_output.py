# Archives the current output folder before re-running analysis.
# Creates timestamped backup in data/archive/.
import sys
import os
import shutil
import argparse
from datetime import datetime

# Ensure the project root directory is added to Python path so config can be imported correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing the output directory path from config
try:
    from config import DATA_OUTPUT_DIR
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

# Function to archive the output directory into a timestamped folder
def archive_output(output_dir: str, custom_name: str = None) -> str:
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
    parser = argparse.ArgumentParser(description='Archive current output folder')
    parser.add_argument('--name', type=str, help='Custom suffix for archive name')
    parser.add_argument('--clear', action='store_true', help='Clear output after archiving')
    args = parser.parse_args()
    
    # Locate the output directory using project root combined with config path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    
    # Display header text for clarity
    print("=" * 60)
    print("  ARCHIVE OUTPUT")
    print("=" * 60)
    
    # Perform the archiving operation
    archive_path = archive_output(output_dir, args.name)
    
    # If archiving was successful, print summary information
    if archive_path:
        print(f"\n✓ Archived to: {archive_path}")
        
        # Count total files inside the archived directory
        file_count = sum(1 for _ in os.walk(archive_path) for _ in _[2])
        print(f"  Files archived: {file_count}")
        
        # If user specified --clear, remove all items inside the output directory
        if args.clear:
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                
                # Remove regular files
                if os.path.isfile(item_path):
                    os.remove(item_path)
                
                # Remove folders except for 'charts'
                elif os.path.isdir(item_path) and item != 'charts':
                    shutil.rmtree(item_path)
                
                # If folder is 'charts', empty it but keep the folder itself
                elif item == 'charts':
                    for chart in os.listdir(item_path):
                        os.remove(os.path.join(item_path, chart))
            
            print("✓ Cleared output directory")
        
        # Inform user that further analysis steps can now be executed freshly
        print("\nYou can now re-run analysis steps 3-7.")
    
    # If nothing was archived, print message
    else:
        print("\nNothing to archive.")

# Ensure the main function runs only when script is executed directly
if __name__ == "__main__":
    main()
