import logging
import numpy as np
from osgeo import gdal
from typing import List
import pandas as pd

logger = logging.getLogger(__name__)

def calculate_slope(dem_array: List[List], cell_size: float):
    """
    Calculates slope from a DEM array.

    Args:
        dem_array (np.ndarray): 2D NumPy array of elevation values.
        cell_size (float): The size of each cell/pixel in the DEM (e.g., meters).

    Returns:
        np.ndarray: 2D NumPy array of slope values in degrees.
    """
    dy, dx = np.gradient(dem_array, cell_size)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    return slope_deg

def calculate_aspect(dem_array: List[List], cell_size: float):
    """
    Calculates aspect from a DEM array.

    Args:
        dem_array (np.ndarray): 2D NumPy array of elevation values.
        cell_size (float): The size of each cell/pixel in the DEM.

    Returns:
        np.ndarray: 2D NumPy array of aspect values in degrees (0-360).
    """
    dy, dx = np.gradient(dem_array, cell_size)
    aspect_rad = np.arctan2(-dy, dx)  # Note: -dy for cartesian to geographic convention
    aspect_deg = np.degrees(aspect_rad)
    # Adjust aspect to 0-360 degrees, North = 0/360
    # Common conversion: 90 - aspect_deg for angles from East counter-clockwise
    # Or, to match common GIS tools (0 North, clockwise):
    aspect_deg = (450 - aspect_deg) % 360 # Adjusts and handles negative results from arctan2
    # A slightly different adjustment was in the source:
    # aspect_deg = np.where(aspect_deg < 0, 90.0 - aspect_deg, 450.0 - aspect_deg) % 360
    # The above is a common adjustment, if dx, dy are considered as East, North respectively
    return aspect_deg

def calculate_curvature(dem_array, cell_size):
    """
    Calculates a general curvature (Laplacian) from a DEM array.

    Args:
        dem_array (np.ndarray): 2D NumPy array of elevation values.
        cell_size (float): The size of each cell/pixel in the DEM.

    Returns:
        np.ndarray: 2D NumPy array of curvature values.
    """
    # First derivatives
    dy, dx = np.gradient(dem_array, cell_size)
    
    # Second derivatives
    d2y_dy, d2x_dy = np.gradient(dy, cell_size) # d(dy)/dy, d(dx)/dy
    d2y_dx, d2x_dx = np.gradient(dx, cell_size) # d(dy)/dx, d(dx)/dx

    # General curvature (Laplacian)
    # The source used d2x + d2y from a nested gradient call which might be interpreted differently.
    # Typically, Laplacian is d^2z/dx^2 + d^2z/dy^2
    # Using d2x_dx and d2y_dy:
    curvature = d2x_dx + d2y_dy
    return curvature

def calculate_contours(dem_array, cell_x_coords, cell_y_coords, levels):
    """
    Generates contour lines from a DEM array.

    Args:
        dem_array (np.ndarray): 2D NumPy array of elevation values.
        cell_x_coords (np.ndarray): 1D array of x-coordinates for columns.
        cell_y_coords (np.ndarray): 1D array of y-coordinates for rows.
        levels (list or int): Elevation levels for which to generate contours.

    Returns:
        list: A list of NumPy arrays, where each array contains the (x, y)
              vertices of a contour line segment.
    """
    fig, ax = plt.subplots()
    # contour requires X, Y meshgrid for actual coordinates, or assumes pixel indices
    cs = ax.contour(cell_x_coords, cell_y_coords, dem_array, levels=levels)
    plt.close(fig)  # Close plot to avoid display

    contours_data = []
    for i, collection in enumerate(cs.collections):
        level_contours = []
        for path in collection.get_paths():
            level_contours.append(path.vertices)
        contours_data.append({
            'level': cs.levels[i] if isinstance(cs.levels, (list, np.ndarray)) else cs.levels,
            'paths': level_contours
        })
    return contours_data

def calculate_flow_direction_d8(dem_array):
    """
    Calculates D8 flow direction from a DEM array.

    Args:
        dem_array (np.ndarray): 2D NumPy array of elevation values.

    Returns:
        np.ndarray: 2D NumPy array of flow direction codes.
                    (Codes might be: 1=E, 2=NE, 4=N, 8=NW, 16=W, 32=SW, 64=S, 128=SE,
                     or other conventions like 1-8, or powers of 2).
                     The example uses powers of 2.
    """
    rows, cols = dem_array.shape
    flow_dir = np.zeros_like(dem_array, dtype=np.uint8)
    
    # D8 direction codes (powers of 2, right to bottom-right clockwise)
    # E, SE, S, SW, W, NW, N, NE
    # Codes: 1  2  4  8   16  32  64 128 (GIS standard from ESRI)
    # The source [7] used:
    #   [[128, 64, 32],  (NW, N, NE in its comment mapping)
    #    [  1,  0, 16],  (W, center, E)
    #    [  2,  4,  8]]  (SW, S, SE)
    # This seems to be a non-standard mapping or a typo in the comment.
    # Let's use a common convention:
    # 1=E, 2=NE, 4=N, 8=NW, 16=W, 32=SW, 64=S, 128=SE
    # Offsets: (row, col), Code
    # (0,1)=E=1, (-1,1)=NE=2, (-1,0)=N=4, (-1,-1)=NW=8, 
    # (0,-1)=W=16, (1,-1)=SW=32, (1,0)=S=64, (1,1)=SE=128
    
    # Corrected D8 directions and codes (ESRI convention)
    # dx, dy, code
    d_lookup = [
        (0, 1, 1),   # E
        (-1, 1, 2),  # NE
        (-1, 0, 4),  # N
        (-1, -1, 8), # NW
        (0, -1, 16), # W
        (1, -1, 32), # SW
        (1, 0, 64),  # S
        (1, 1, 128)  # SE
    ]

    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            center_elev = dem_array[r, c]
            max_drop = 0
            best_dir = 0 # Default for flat areas/pits

            for dr, dc, d_code in d_lookup:
                nr, nc = r + dr, c + dc
                neighbor_elev = dem_array[nr, nc]
                drop = (center_elev - neighbor_elev) # Drop is positive if flowing down
                
                # For D8, typically uses drop / distance for true slope
                # Simple D8 often just uses raw elevation difference
                # distance = np.sqrt(dr**2 + dc**2) # 1 for cardinal, sqrt(2) for diagonal
                # current_slope = drop / distance if distance > 0 else 0
                
                # Using simple drop as per source [7] logic structure
                if drop > max_drop:
                    max_drop = drop
                    best_dir = d_code
            
            flow_dir[r, c] = best_dir
    return flow_dir

def get_dem_features_with_coordinates(dem_path):
    """
    Extracts coordinates, elevation, and other derived features from a DEM file.

    Args:
        dem_path (str): Path to the DEM file.

    Returns:
        pandas.DataFrame or None: A DataFrame with columns for x, y, elevation,
                                  and other derived features. Returns None if an error occurs.
    """
    try:
        dataset = gdal.Open(dem_path)
        if dataset is None:
            print(f"Error: Could not open DEM file: {dem_path}")
            return None

        geotransform = dataset.GetGeoTransform()
        x_origin = geotransform[0]  # Top-left X
        y_origin = geotransform[3]  # Top-left Y
        pixel_width = geotransform[1]  # W-E pixel resolution
        pixel_height = geotransform[5] # N-S pixel resolution (negative)
        x_rotation = geotransform[2]   # Row rotation (usually 0)
        y_rotation = geotransform[4]   # Column rotation (usually 0)

        band = dataset.GetRasterBand(1)
        elevation_array = band.ReadAsArray()
        nodata_value = band.GetNoDataValue()
        cols = band.XSize
        rows = band.YSize

        # Calculate derived features
        # Cell sizes for feature calculations (absolute values for height)
        cell_size_x_geo = pixel_width # if geotransform[2] and geotransform[4] are 0
        cell_size_y_geo = abs(pixel_height) # if geotransform[2] and geotransform[4] are 0
        # Note: If DEM is in geographic coords (lat/lon), cell_size for slope etc.
        # might need to be converted to meters or scaled.
        # For simplicity here, assuming projected CRS or appropriate scaling is handled.

        # Example of calculating features (replace with actual functions)
        slope_array = calculate_slope_placeholder(elevation_array, cell_size_x_geo, cell_size_y_geo)
        aspect_array = calculate_aspect_placeholder(elevation_array, cell_size_x_geo, cell_size_y_geo)
        # curvature_array = calculate_curvature(elevation_array, cell_size_x_geo, cell_size_y_geo)
        # hillshade_array = calculate_hillshade(elevation_array, cell_size_x_geo, cell_size_y_geo)


        output_data = []
        for r_idx in range(rows):
            for c_idx in range(cols):
                elevation = elevation_array[r_idx, c_idx]

                # Skip NoData pixels
                if nodata_value is not None and elevation == nodata_value:
                    continue

                # Calculate coordinate of the center of the pixel
                x_coord = x_origin + (c_idx + 0.5) * pixel_width + (r_idx + 0.5) * x_rotation
                y_coord = y_origin + (c_idx + 0.5) * y_rotation + (r_idx + 0.5) * pixel_height
                
                # Get corresponding feature values
                slope = slope_array[r_idx, c_idx]
                aspect = aspect_array[r_idx, c_idx]
                # curvature = curvature_array[r_idx, c_idx]
                # hillshade = hillshade_array[r_idx, c_idx]

                output_data.append({
                    'x': x_coord,
                    'y': y_coord,
                    'elevation': elevation,
                    'slope': slope,
                    'aspect': aspect,
                    # 'curvature': curvature,
                    # 'hillshade': hillshade
                })
        
        dataset = None # Close the dataset
        
        if not output_data:
            print("Warning: No data points extracted. DEM might be empty or all NoData.")
            return pd.DataFrame() # Return empty DataFrame

        return pd.DataFrame(output_data)

    except Exception as e:
        print(f"An error occurred: {e}")
        if 'dataset' in locals() and dataset is not None:
            dataset = None # Ensure dataset is closed on error
        return None
