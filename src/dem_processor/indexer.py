import rtree
import rasterio
import os
import glob
import geopandas as gpd
import pickle
from config import INDEX_FILE_PREFIX, INFO_LIST_FILE, RASTER_DIRS, RASTER_TYPE_PATTERNS


def index_raster_files(raster_dirs, raster_type_patterns):
    """
    Finds raster files in specified directories, extracts their bounds and type,
    and builds an R-tree index.

    Returns:
        tuple: (spatial_index, raster_info_list)
               spatial_index (rtree.index.Index): R-tree index of raster bounds.
               raster_info_list (list): List of dicts [{id, path, type, bounds, crs}, ...]
    """
    raster_info_list = []
    raster_id_counter = 0

    print("Indexing raster files...")
    for directory in raster_dirs:
        rtree_path = os.path.join(directory, 'rtree')
        # TODO Fix Saving with overwrite and loading
        spatial_index = rtree.index.Index()
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
                        crs = src.crs # Keep the CRS object
                        raster_info = {
                            'id': raster_id_counter,
                            'path': filepath,
                            'type': feature_type,
                            'bounds': bounds,
                            'crs': crs
                        }
                        # rtree expects (minx, miny, maxx, maxy)
                        spatial_index.insert(raster_id_counter, (bounds.left, bounds.bottom, bounds.right, bounds.top))
                        raster_info_list.append(raster_info)
                        raster_id_counter += 1
                        # print(f" Indexed: {os.path.basename(filepath)} ({feature_type})")

                except rasterio.errors.RasterioIOError as e:
                    print(f"Error opening or reading raster file {filepath}: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred processing {filepath}: {e}")

    print(f"Finished indexing. Total rasters indexed: {len(raster_info_list)}")
    return spatial_index, raster_info_list

def save_raster_index(spatial_index, raster_info_list, index_prefix, info_list_path):
    """Saves the spatial index and raster info list to files."""
    print(f"Saving index to {index_prefix}.* and info list to {info_list_path}")
    try:
        # Save the rtree index
        spatial_index.close()

        # Save the raster info list using pickle
        with open(info_list_path, 'wb') as f:
            pickle.dump(raster_info_list, f)

        print("Index and info list saved successfully.")
    except Exception as e:
        print(f"Error saving index or info list: {e}")

def load_raster_index(index_prefix, info_list_path):
    """Loads the spatial index and raster info list from files."""
    print(f"Attempting to load index from {index_prefix}.* and info list from {info_list_path}")
    try:
        # Load the rtree index
        # The index files must exist for this to work
        spatial_index = rtree.index.Index(index_prefix)

        # Load the raster info list
        with open(info_list_path, 'rb') as f:
            raster_info_list = pickle.load(f)

        print("Index and info list loaded successfully.")
        return spatial_index, raster_info_list
    except rtree.index.IndexError:
        print(f"Index files not found at {index_prefix}.*")
        return None, None
    except FileNotFoundError:
        print(f"Info list file not found at {info_list_path}")
        return None, None
    except Exception as e:
        print(f"Error loading index or info list: {e}")
        return None, None


def extract_raster_features(x, y, spatial_index, raster_info_list):
    """
    Extracts feature values from rasters at a given point (x, y).
    Assumes point (x,y) is in the SAME CRS as the raster files.

    Args:
        x (float): X coordinate of the point.
        y (float): Y coordinate of the point.
        spatial_index (rtree.index.Index): The R-tree index of raster bounds.
        raster_info_list (list): List of dicts containing raster information.

    Returns:
        dict: A dictionary where keys are feature types (e.g., 'Elevation', 'Slope')
              and values are the extracted raster values at the point.
              Returns an empty dict if no rasters cover the point or errors occur.
    """
    point_features = {}
    point_bbox = (x, y, x, y) # Bbox for the point query

    # Find intersecting rasters using the R-tree index
    intersecting_raster_ids = list(spatial_index.intersection(point_bbox))

    if not intersecting_raster_ids:
        # print(f"Point ({x}, {y}) is outside the bounds of all indexed rasters.")
        return point_features

    intersecting_rasters = [info for info in raster_info_list if info['id'] in intersecting_raster_ids]

    processed_types = set()

    for r_info in intersecting_rasters:
        feature_type = r_info['type']

        if feature_type in processed_types:
            continue

        try:
            # Open the raster file. Use 'with' for safety.
            with rasterio.open(r_info['path']) as src:
                # Check if the point is within the raster's bounds *before* sampling
                # This can prevent rasterio errors on edge cases
                if not (src.bounds.left <= x <= src.bounds.right and src.bounds.bottom <= y <= src.bounds.top):
                     print(f"Point ({x}, {y}) outside bounds of {r_info['path']}, skipping sample.")
                     continue # Skip this raster

                # Sample the pixel value. src.sample takes a list of (x,y) tuples.
                # It returns an iterator of arrays. We expect one array [value].
                # We get the first (and only) element of the first array.
                pixel_value = list(src.sample([(x, y)]))[0][0]

                # Handle potential NoData values if necessary
                # if pixel_value == src.nodata or pixel_value is None:
                #     # Optionally set to None, NaN, or skip adding the feature
                #     point_features[feature_type] = None # Example: set to None
                # else:
                point_features[feature_type] = pixel_value

                processed_types.add(feature_type)

        except rasterio.errors.RasterioIOError as e:
            print(f"Error sampling raster file {r_info['path']} at ({x}, {y}): {e}")
        except IndexError:
             # Can happen if src.sample returns an empty list, e.g., point is outside valid area but inside loose bounds
             print(f"Error sampling raster file {r_info['path']} at ({x}, {y}): Point sample failed.")
        except Exception as e:
            print(f"An unexpected error occurred sampling {r_info['path']} at ({x}, {y}): {e}")

    return point_features

# --- Example Usage ---
if __name__ == "__main__":
    # Define paths for saving/loading the index
    index_path_prefix = INDEX_FILE_PREFIX
    info_list_filepath = INFO_LIST_FILE

    # 1. Attempt to load the existing index
    raster_index, raster_details = load_raster_index(index_path_prefix, info_list_filepath)

    # 2. If loading failed (index files not found), build the index and save it
    if raster_index is None or raster_details is None:
        print("Index not found or failed to load. Building index...")
        raster_index, raster_details = index_raster_files(RASTER_DIRS, RASTER_TYPE_PATTERNS)

        if raster_index and raster_details: # Only save if indexing was successful
             save_raster_index(raster_index, raster_details, index_path_prefix, info_list_filepath)
        else:
             print("Failed to build index. Cannot proceed with feature extraction.")
             exit() # Exit if indexing failed

    # 3. Now you have the spatial_index and raster_details (either loaded or newly built)
    #    Proceed with feature extraction using these objects.

    # Prepare your input points (e.g., borehole locations or prediction points)
    # Make sure these points are in the SAME CRS as your raster data (HARN83 Washington South Meters)
    # Replace with loading your actual point data
    sample_points = [
        (400000.0, 4800000.0), # Example point 1 (replace with your actual coordinates)
        (410000.0, 4810000.0), # Example point 2
        (10.0, 10.0),          # Example point outside coverage
        (390000.0, 4700000.0)  # Example point that should be covered
    ]
    print("\nExtracting features for sample points...")
    all_points_features = []

    for i, (p_x, p_y) in enumerate(sample_points):
        features = extract_raster_features(p_x, p_y, raster_index, raster_details)
        print(f"Point {i+1} ({p_x:.2f}, {p_y:.2f}): {features}")
        all_points_features.append({'X': p_x, 'Y': p_y, **features})

    # You can now use the all_points_features list (or convert to DataFrame/GeoDataFrame)
    # as input for your ML model training or prediction.

    # Example of converting to DataFrame
    # import pandas as pd
    # features_df = pd.DataFrame(all_points_features)
    # print("\nDataFrame of extracted features:")
    # print(features_df)