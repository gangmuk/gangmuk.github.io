import os
import sys

def rename_files_replace_first_dash():
    """
    Rename files in current directory by replacing the first dash (-) with a comma (,)
    """
    # Get current directory
    current_dir = os.getcwd()
    
    # List to store renamed files info
    renamed_files = []
    
    # Get all files in current directory
    files = os.listdir(current_dir)
    
    print(f"Found {len(files)} items in current directory")
    print("Processing files...\n")
    
    for filename in files:
        # Check if it's a file (not a directory) and contains a dash
        if os.path.isfile(filename) and '-' in filename:
            # Replace only the first dash with comma
            new_filename = filename.replace('-', ',', 1)
            
            try:
                # Rename the file
                os.rename(filename, new_filename)
                renamed_files.append((filename, new_filename))
                print(f"✓ Renamed: {filename} -> {new_filename}")
            except OSError as e:
                print(f"✗ Error renaming {filename}: {e}")
        elif os.path.isfile(filename):
            print(f"- Skipped (no dash): {filename}")
        else:
            print(f"- Skipped (directory): {filename}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Summary: {len(renamed_files)} files renamed successfully")
    if renamed_files:
        print("\nRenamed files:")
        for old, new in renamed_files:
            print(f"  {old} -> {new}")
    
    return renamed_files

def preview_changes():
    """
    Preview what changes would be made without actually renaming files
    """
    current_dir = os.getcwd()
    files = os.listdir(current_dir)
    
    print("PREVIEW MODE - No files will be renamed")
    print(f"Found {len(files)} items in current directory")
    print("Files that would be renamed:\n")
    
    changes = []
    for filename in files:
        if os.path.isfile(filename) and '-' in filename:
            new_filename = filename.replace('-', ',', 1)
            changes.append((filename, new_filename))
            print(f"  {filename} -> {new_filename}")
    
    if not changes:
        print("  No files with dashes found to rename")
    
    print(f"\nTotal files that would be renamed: {len(changes)}")
    return changes

# Main execution
if __name__ == "__main__":
    print("Photo File Renamer - Replace first dash with comma")
    print("="*50)
    
    # First show preview
    print("\n1. PREVIEW CHANGES:")
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    preview_changes(target_dir)
    
    # Ask for confirmation
    print("\n" + "="*50)
    confirm = input("Do you want to proceed with renaming? (y/N): ").lower().strip()
    
    if confirm == 'y' or confirm == 'yes':
        print("\n2. RENAMING FILES:")
        rename_files_replace_first_dash()
    else:
        print("Operation cancelled. No files were renamed.")
    
    print("\nDone!")