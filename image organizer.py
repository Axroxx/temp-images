#!/usr/bin/env python3
"""
Media File Organizer
Organizes images and videos into date-based folders with RAW and video subfolders.
If consecutive days are found, files from the second day are moved to the first day's folder.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

# Supported file formats
IMAGE_FORMATS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
    '.webp', '.ico', '.svg', '.heic', '.heif'
}

RAW_FORMATS = {
    '.raw', '.cr2', '.cr3', '.nef', '.arw', '.orf', '.rw2', 
    '.pef', '.srw', '.x3f', '.dng', '.raf', '.3fr', '.fff',
    '.dcr', '.kdc', '.srf', '.mrw', '.nrw', '.rwl'
}

VIDEO_FORMATS = {
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.3g2', '.mts', '.m2ts', '.ts', '.mxf',
    '.asf', '.rm', '.rmvb', '.vob', '.ogv', '.drc', '.gif',
    '.gifv', '.mng', '.qt', '.yuv', '.amv', '.mp2', '.mpe',
    '.mpg', '.mpeg', '.m2v', '.svi', '.f4v', '.f4p', '.f4a', '.f4b'
}

def get_file_date(file_path):
    """Get the creation/modification date of a file."""
    try:
        # Try to get creation time first, fall back to modification time
        if os.name == 'nt':  # Windows
            creation_time = os.path.getctime(file_path)
        else:  # Unix/Linux/Mac
            stat = os.stat(file_path)
            creation_time = getattr(stat, 'st_birthtime', stat.st_mtime)
        
        return datetime.fromtimestamp(creation_time).date()
    except Exception as e:
        print(f"Error getting date for {file_path}: {e}")
        return None

def is_media_file(file_path):
    """Check if file is a supported media format."""
    suffix = file_path.suffix.lower()
    return suffix in (IMAGE_FORMATS | RAW_FORMATS | VIDEO_FORMATS)

def get_file_category(file_path):
    """Determine if file is raw, video, or regular image."""
    suffix = file_path.suffix.lower()
    if suffix in RAW_FORMATS:
        return 'raw'
    elif suffix in VIDEO_FORMATS:
        return 'video'
    elif suffix in IMAGE_FORMATS:
        return 'image'
    else:
        return None

def consolidate_consecutive_days(date_groups):
    """Merge consecutive days, with second day files going to first day."""
    sorted_dates = sorted(date_groups.keys())
    consolidated = {}
    skip_dates = set()
    
    for i, current_date in enumerate(sorted_dates):
        if current_date in skip_dates:
            continue
            
        # Check if next date is consecutive
        if i + 1 < len(sorted_dates):
            next_date = sorted_dates[i + 1]
            if next_date == current_date + timedelta(days=1):
                # Merge next day into current day
                consolidated[current_date] = date_groups[current_date] + date_groups[next_date]
                skip_dates.add(next_date)
                print(f"Merging {next_date} into {current_date}")
            else:
                consolidated[current_date] = date_groups[current_date]
        else:
            consolidated[current_date] = date_groups[current_date]
    
    return consolidated

def create_folder_structure(base_path, date_str):
    """Create the folder structure for a given date."""
    date_folder = base_path / date_str
    raw_folder = date_folder / "RAW"
    video_folder = date_folder / "VIDEO"
    
    date_folder.mkdir(exist_ok=True)
    raw_folder.mkdir(exist_ok=True)
    video_folder.mkdir(exist_ok=True)
    
    return {
        'date': date_folder,
        'raw': raw_folder,
        'video': video_folder
    }

def organize_files(source_path, dry_run=False):
    """Organize media files into date-based folders."""
    source_path = Path(source_path)
    
    if not source_path.exists():
        print(f"Error: Source path '{source_path}' does not exist.")
        return
    
    print(f"Scanning for media files in: {source_path}")
    
    # Group files by date
    date_groups = defaultdict(list)
    total_files = 0
    
    # Recursively find all media files
    for file_path in source_path.rglob('*'):
        if file_path.is_file() and is_media_file(file_path):
            file_date = get_file_date(file_path)
            if file_date:
                date_groups[file_date].append(file_path)
                total_files += 1
    
    print(f"Found {total_files} media files across {len(date_groups)} dates")
    
    if not date_groups:
        print("No media files found.")
        return
    
    # Consolidate consecutive days
    consolidated_groups = consolidate_consecutive_days(date_groups)
    
    print(f"After consolidation: {len(consolidated_groups)} date groups")
    
    # Process each date group
    for date, files in consolidated_groups.items():
        date_str = date.strftime('%Y-%m-%d')
        print(f"\nProcessing {date_str} ({len(files)} files):")
        
        if dry_run:
            print(f"  [DRY RUN] Would create folder: {date_str}")
        else:
            folders = create_folder_structure(source_path, date_str)
        
        # Categorize and move files
        categories = {'raw': 0, 'video': 0, 'image': 0}
        
        for file_path in files:
            category = get_file_category(file_path)
            if not category:
                continue
                
            categories[category] += 1
            
            if dry_run:
                if category == 'raw':
                    print(f"  [DRY RUN] Would move to RAW: {file_path.name}")
                elif category == 'video':
                    print(f"  [DRY RUN] Would move to VIDEO: {file_path.name}")
                else:
                    print(f"  [DRY RUN] Would move to date folder: {file_path.name}")
            else:
                try:
                    if category == 'raw':
                        dest_path = folders['raw'] / file_path.name
                    elif category == 'video':
                        dest_path = folders['video'] / file_path.name
                    else:
                        dest_path = folders['date'] / file_path.name
                    
                    # Handle filename conflicts
                    counter = 1
                    original_dest = dest_path
                    while dest_path.exists():
                        stem = original_dest.stem
                        suffix = original_dest.suffix
                        dest_path = original_dest.parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    shutil.move(str(file_path), str(dest_path))
                    print(f"  Moved: {file_path.name} -> {dest_path.relative_to(source_path)}")
                    
                except Exception as e:
                    print(f"  Error moving {file_path.name}: {e}")
        
        print(f"  Summary: {categories['image']} images, {categories['raw']} raw files, {categories['video']} videos")

def main():
    parser = argparse.ArgumentParser(description='Organize media files by date')
    parser.add_argument('path', help='Path to scan for media files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually moving files')
    
    args = parser.parse_args()
    
    print("Media File Organizer")
    print("===================")
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be moved")
    
    organize_files(args.path, dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\nOrganization complete!")
    else:
        print("\nDry run complete! Use without --dry-run to actually move files.")

if __name__ == "__main__":
    main()