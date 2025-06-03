import zipfile
import os

# --- Configuration ---
# Directory containing your downloaded .zip DEM files
SOURCE_DIR = "../soilense_data/DEM/washington_10meter_dem_tiles"

# Directory where the unzipped .tif files should be saved
# It's good practice to unzip into a subfolder to keep things organized
DESTINATION_DIR = os.path.join(SOURCE_DIR, "unzipped_dems")
# ---------------------

def unzip_file(zip_filepath, dest_dir):
    """Unzips a single zip file to a destination directory."""
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            print(f"Unzipping: {os.path.basename(zip_filepath)}")
            # Extract all contents to the destination directory
            zip_ref.extractall(dest_dir)
            print(f"Successfully unzipped to {dest_dir}")
            return True
    except zipfile.BadZipFile:
        print(f"Error: {os.path.basename(zip_filepath)} is not a valid zip file.")
        return False
    except Exception as e:
        print(f"An error occurred while unzipping {os.path.basename(zip_filepath)}: {e}")
        return False

def unzip_all_zips_in_directory(source_dir, destination_dir):
    """Finds all .zip files in a directory and unzips them."""

    # Ensure the destination directory exists
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        print(f"Created destination directory: {destination_dir}")
    else:
        print(f"Destination directory already exists: {destination_dir}")

    print(f"Searching for .zip files in: {source_dir}")
    files_found = os.listdir(source_dir)
    zip_count = 0
    unzipped_count = 0

    for filename in files_found:
        # Construct the full path to the file
        filepath = os.path.join(source_dir, filename)

        # Check if it's a file and ends with .zip (case-insensitive check is safer)
        if os.path.isfile(filepath) and filename.lower().endswith('.zip'):
            zip_count += 1
            if unzip_file(filepath, destination_dir):
                unzipped_count += 1

    print("-" * 20)
    print(f"Finished checking directory. Found {zip_count} .zip files.")
    print(f"Attempted to unzip {zip_count} files, {unzipped_count} were successfully processed.")


if __name__ == "__main__":
    # Resolve the source directory path based on the script's current working directory
    resolved_source_dir = os.path.abspath(SOURCE_DIR)
    # Resolve the destination directory path
    resolved_destination_dir = os.path.abspath(DESTINATION_DIR)

    print(f"Script's current working directory: {os.getcwd()}")
    print(f"Resolved source directory: {resolved_source_dir}")
    print(f"Resolved destination directory: {resolved_destination_dir}")
    print("-" * 20)


    # Check if the source directory exists before proceeding
    if not os.path.exists(resolved_source_dir):
        print(f"Error: Source directory not found at {resolved_source_dir}")
    else:
        unzip_all_zips_in_directory(resolved_source_dir, resolved_destination_dir)
