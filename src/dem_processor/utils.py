from logging import Logger
import numpy as np
from osgeo import gdal, osr
from typing import List

def handle_dem_nodata(dem_array: List[List], nodata_value: float, logger: Logger) -> np.ndarray:
    dem_array_handled = dem_array.astype(np.float64)
    if nodata_value is not None:
        logger.info(f"Handling NoData value: {nodata_value}")
        nodata_mask = (dem_array_handled == nodata_value)
        dem_array_handled[nodata_mask] = np.nan
        
        total_cell_count = dem_array_handled.size
        nodata_cell_count = np.sum(nodata_mask)
        data_cell_count = total_cell_count - nodata_cell_count
        logger.info(f"Number of cells: {total_cell_count}")
        logger.info(f"Number of NoData cells found: {nodata_cell_count}")
        logger.info(f"Number of data cells found: {data_cell_count}")
        logger.info(f"Data type after handling: {dem_array_handled.dtype}")

    else:
        logger.info("No explicit NoData value found in raster metadata. Proceeding without handling.")
    return dem_array_handled

def get_features_at_coordinates(coordinates):
    features = []
    for coord in coordinates:
        grid_bounds = find_grid_bounds(coord)
        relevant_dem_ids = set()
        for grid_id in grid_bounds:
            relevant_dem_ids.update(grid_to_dem[grid_id])

        for dem_id in relevant_dem_ids:
            # Fetch and process the DEM data
            slope, other_features = fetch_and_process_dem(dem_files[dem_id], coord)
            features.append((slope, other_features))

    return features

def find_grid_bounds(coord):
    minx, miny = coord
    grid_bounds = [(minx + i * cell_size, miny + j * cell_size, minx + (i + 1) * cell_size, miny + (j + 1) * cell_size)
                  for i in range(int((maxx - minx) / cell_size)) for j in range(int((maxy - miny) / cell_size))]
    return grid_bounds

def get_dem_info(dem_path=None, dataset=None):
    """
    Retrieves and prints information about a DEM's scale and units.

    Args:
        dem_path (str): Path to the DEM file.
    """
    try:
        if dataset is None and dem_path is not None:
            dataset = gdal.Open(dem_path)
        if dataset is None:
            print(f"Error: Could not open DEM file: {dem_path}")
            return

        print(f"--- DEM Information for: {dem_path} ---")

        # --- Horizontal Units and Scale (Resolution) ---
        geotransform = dataset.GetGeoTransform()
        # geotransform[0] = top-left X
        # geotransform[1] = W-E pixel resolution (pixel width)
        # geotransform[2] = row rotation (typically 0)
        # geotransform[3] = top-left Y
        # geotransform[4] = column rotation (typically 0)
        # geotransform[5] = N-S pixel resolution (pixel height, typically negative)

        pixel_width = geotransform[1]
        pixel_height = abs(geotransform[5]) # Use absolute value for height

        print(f"\nHorizontal Scale (Pixel Resolution):")
        print(f"  Pixel Width (X-direction): {pixel_width}")
        print(f"  Pixel Height (Y-direction): {pixel_height}")

        projection_wkt = dataset.GetProjection()
        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection_wkt)

        horizontal_units = "Unknown"
        if srs.IsGeographic():
            # Geographic Coordinate System (units typically degrees)
            horizontal_units = srs.GetAttrValue("GEOGCS|UNIT", 0) # Usually 'degree'
            if horizontal_units is None or "degree" not in horizontal_units.lower():
                 horizontal_units = "Degrees" # Fallback if unit name isn't explicit
        elif srs.IsProjected():
            # Projected Coordinate System (units typically meters or feet)
            horizontal_units = srs.GetAttrValue("PROJCS|UNIT", 0) # e.g., 'metre', 'foot'
            if horizontal_units is None:
                 # Try GetLinearUnitsName for older GDAL or different WKT structures
                 horizontal_units = srs.GetLinearUnitsName()
        
        print(f"Horizontal Units: {horizontal_units}")

        # --- Vertical Units (Z-values) ---
        band = dataset.GetRasterBand(1)
        vertical_units_from_band = band.GetUnitType() # May return 'metre', 'foot', or empty

        print(f"\nVertical Units (Elevation Values):")
        if vertical_units_from_band:
            print(f"  Reported by GDAL Band.GetUnitType(): '{vertical_units_from_band}'")
        else:
            print(f"  GDAL Band.GetUnitType() did not report specific units.")
            print(f"  Vertical units often need to be inferred from metadata or data range.")

        # Check general metadata for hints
        metadata = dataset.GetMetadata()
        if metadata:
            print("  General DEM Metadata:")
            for key, value in metadata.items():
                if "unit" in key.lower() or "zunit" in key.lower(): # Look for unit-related keys
                    print(f"    {key}: {value}")
        
        # Examine elevation value range for plausibility
        min_val = band.GetMinimum()
        max_val = band.GetMaximum()
        if min_val is None or max_val is None:
            try:
                (min_val, max_val) = band.ComputeRasterMinMax(True)
            except RuntimeError: # Handle cases where it can't be computed
                min_val, max_val = "N/A", "N/A"

        print(f"  Elevation Range (min, max): ({min_val}, {max_val})")
        print(f"  Interpret range: If max elevation is ~8850, units are likely meters (Everest).")
        print(f"  If max is e.g. ~14000 for a US mountain range, units could be feet.")
        print(f"  Always verify with external metadata or source documentation if unsure.")
        
        # --- Scale Factor for gdaldem (Ratio of Vertical to Horizontal Units) ---
        print(f"\nScale Factor for 'gdaldem' (if horizontal and vertical units differ):")
        if horizontal_units.lower() == "degrees" and (vertical_units_from_band.lower() == "metre" or "meter" in str(min_val) + str(max_val) or not vertical_units_from_band): # common case
            print(f"  If horizontal units are degrees and vertical units are meters, typical scale factor: ~111120")
        elif horizontal_units.lower() == "degrees" and (vertical_units_from_band.lower() == "foot" or "feet" in str(min_val) + str(max_val)):
            print(f"  If horizontal units are degrees and vertical units are feet, typical scale factor: ~370400")
        elif horizontal_units.lower() == vertical_units_from_band.lower() and horizontal_units != "Unknown":
            print(f"  Horizontal and vertical units appear to be the same ('{horizontal_units}'). Scale factor: 1")
        else:
            print(f"  Determine based on confirmed horizontal and vertical units.")
        
        dataset = None # Close the dataset

    except Exception as e:
        print(f"An error occurred: {e}")
        if 'dataset' in locals() and dataset is not None:
            dataset = None

