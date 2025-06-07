import rtree
import rasterio
import os
import glob
import pickle
from config import INDEX_FILE_PREFIX, INFO_LIST_FILE, RASTER_DIRS, RASTER_TYPE_PATTERNS

# Helper function to save just the info list (separated from index saving)
def save_raster_info(raster_info_list, info_list_path):
    """Saves the raster info list to a pickle file."""
    print(f"Saving raster info list to {info_list_path}")
    try:
        with open(info_list_path, 'wb') as f:
            pickle.dump(raster_info_list, f)
        print("Info list saved successfully.")
    except Exception as e:
        print(f"Error saving info list: {e}")

# Modified function to build the persistent index and save info list
def build_and_save_raster_index(raster_dirs, raster_type_patterns, index_prefix, info_list_path):
    """
    Finds raster files, extracts their info, builds a *persistent* R-tree index
    at the specified prefix, and saves the raster info list.

    Args:
        raster_dirs (list): Directories to search.
        raster_type_patterns (dict): Patterns for file types.
        index_prefix (str): Prefix path for the R-tree index files (e.g., "path/to/my_index").
                            R-tree will create/use files like my_index.idx and my_index.dat.
        info_list_path (str): Path to save the raster info list pickle file.

    Returns:
        tuple: (spatial_index, raster_info_list) if successful, (None, None) otherwise.
               The returned spatial_index is the *newly created and saved* persistent index,
               opened for reading.
    """
    raster_info_list = []
    raster_id_counter = 0

    print(f"Building persistent R-tree index at {index_prefix}.*")
    try:
        # Create a persistent index. This tells rtree to manage index files
        # at the given prefix. overwrite=True ensures we start fresh.
        properties = rtree.index.Property()
        properties.overwrite = True # Required to build a new index, overwriting existing files
        # For rtree versions < 0.9.x, you might need: spatial_index = rtree.index.Index(index_prefix, properties=properties)
        # For rtree versions >= 0.9.x, this is the standard way:
        spatial_index = rtree.index.Index(index_prefix, properties=properties)


    except Exception as e:
        print(f"Error creating persistent R-tree index at {index_prefix}: {e}")
        return None, None

    print("Indexing raster files and populating R-tree...")
    for directory in raster_dirs:
        for feature_type, pattern in raster_type_patterns.items():
            search_pattern = os.path.join(directory, pattern)
            raster_files = glob.glob(search_pattern)

            if not raster_files:
                print(f"Warning: No files found for type '{feature_type}' with pattern '{search_pattern}'")
                continue

            for filepath in raster_files:
                try:
                    with rasterio.open(filepath) as src:
                        bounds = src.bounds
                        crs = src.crs
                        raster_info = {
                            'id': raster_id_counter,
                            'path': filepath,
                            'type': feature_type,
                            'bounds': bounds, # rasterio Bounds object is fine
                            'crs': crs       # rasterio CRS object is fine
                        }
                        # Insert into the persistent index. rtree writes changes to disk.
                        spatial_index.insert(raster_id_counter, (bounds.left, bounds.bottom, bounds.right, bounds.top))
                        raster_info_list.append(raster_info)
                        raster_id_counter += 1
                        # print(f" Indexed: {os.path.basename(filepath)} ({feature_type})")

                except rasterio.errors.RasterioIOError as e:
                    print(f"Error opening or reading raster file {filepath}: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred processing {filepath}: {e}")

    print(f"Finished indexing. Total rasters indexed: {len(raster_info_list)}")

    # Close the index to ensure all pending writes are flushed to disk
    try:
        spatial_index.close()
        print("R-tree index closed successfully (saved to disk).")
    except Exception as e:
         print(f"Error closing R-tree index: {e}")
         # Decide how to handle this error - maybe the index is partially saved?
         # For robust error handling, you might want to remove partially created files here
         return None, None # Indicate failure if closing/saving fails


    # Save the info list separately using the helper function
    save_raster_info(raster_info_list, info_list_path)

    # Re-open the index in read mode for the function's return value
    # This ensures the index object returned is connected to the saved files
    try:
        # Open the existing persistent index (no overwrite=True)
        loaded_index = rtree.index.Index(index_prefix)
        print("Persistent index re-opened for use after saving.")
        return loaded_index, raster_info_list
    except Exception as e:
         print(f"Error re-opening persistent index after saving: {e}")
         return None, None # Failed to load it back


# Function to load persistent index and info list
def load_raster_index(index_prefix, info_list_path):
    """Loads the persistent spatial index and raster info list from files."""
    print(f"Attempting to load persistent index from {index_prefix}.* and info list from {info_list_path}")
    loaded_index = None
    loaded_info_list = None

    try:
        # Load the rtree index from the persistent files
        loaded_index = rtree.index.Index(index_prefix)
        print("R-tree index loaded successfully.")

    except rtree.index.IndexError:
        # This specifically catches if the .idx or .dat files are missing
        print(f"R-tree index files not found at {index_prefix}.*")
        pass # Keep loaded_index as None and try loading info list

    except Exception as e:
        # Catch other potential errors during index loading
        print(f"Error loading R-tree index from {index_prefix}: {e}")
        loaded_index = None # Ensure it's None on other errors


    try:
        # Load the raster info list
        with open(info_list_path, 'rb') as f:
            loaded_info_list = pickle.load(f)
        print("Info list loaded successfully.")
    except FileNotFoundError:
        print(f"Info list file not found at {info_list_path}")
        loaded_info_list = None # Ensure it's None if file not found
    except Exception as e:
        # Catch other potential errors during info list loading (e.g., pickle issues)
        print(f"Error loading info list from {info_list_path}: {e}")
        loaded_info_list = None


    # Check if *both* parts were loaded successfully. Both are needed.
    if loaded_index is not None and loaded_info_list is not None:
         return loaded_index, loaded_info_list
    else:
         # If either component failed to load, return None, None
         print("Loading failed: R-tree index or info list is missing/corrupted.")
         # Good practice: if the index was partially loaded but info list failed, close the index
         if loaded_index:
             try:
                 loaded_index.close()
                 print("Partially loaded R-tree index closed.")
             except Exception as e_close:
                 print(f"Error closing partially loaded R-tree index: {e_close}")
         return None, None