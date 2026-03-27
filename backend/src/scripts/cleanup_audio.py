"""
Script to clean up old audio alert files.
"""
import os
import time
import argparse
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audio_cleanup")

def cleanup_audio_files(directory: str, max_age_days: int):
    """
    Delete files in directory older than max_age_days.
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory not found: {directory}")
        return

    cutoff_time = time.time() - (max_age_days * 86400)
    deleted_count = 0
    total_size_freed = 0

    logger.info(f"Starting cleanup for {directory}, max age: {max_age_days} days")

    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            # Check if it's a file and matches audio extensions
            if os.path.isfile(filepath) and filename.endswith(('.mp3', '.wav')):
                file_mtime = os.path.getmtime(filepath)
                
                if file_mtime < cutoff_time:
                    try:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                        total_size_freed += file_size
                        logger.debug(f"Deleted old file: {filename}")
                    except OSError as e:
                        logger.error(f"Error deleting {filename}: {e}")
        
        logger.info(f"Cleanup complete. Deleted {deleted_count} files. Freed {total_size_freed / 1024 / 1024:.2f} MB.")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up old audio files.")
    parser.add_argument("--dir", required=True, help="Directory to clean")
    parser.add_argument("--days", type=int, default=1, help="Max age in days")
    
    args = parser.parse_args()
    
    cleanup_audio_files(args.dir, args.days)
