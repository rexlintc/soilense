import pyproj

# --- Configuration ---
# Define the Source CRS (your borehole coordinates in Lat/Lon)
# Common Lat/Lon systems for NAD83 data are:
# EPSG:4269 - NAD83
# EPSG:4326 - WGS 84 (often very similar to NAD83, common for GPS/web maps)
# Check your data source documentation if possible. EPSG:4269 is a likely candidate for legacy NAD83 data.
SOURCE_CRS = "EPSG:4269" # Or "EPSG:4326" if your data is WGS 84

# Define the Target CRS (NAD83 Washington South in US Survey Feet)
# This is the specific ESRI code you mentioned: NAD_1983_2011_StatePlane_Washington_South_FIPS_4602_Ft_US
TARGET_CRS = "ESRI:103181" # Or the corresponding EPSG code if available (less common for ESRI variants)
# You can verify this CRS definition using pyproj:
# target_crs_obj = pyproj.CRS(TARGET_CRS)
# print(target_crs_obj.axis_info) # Shows units, etc.

# --- Transformation ---
try:
    # Create CRS objects
    src_crs = pyproj.CRS(SOURCE_CRS)
    tgt_crs = pyproj.CRS(TARGET_CRS)

    # Create a transformer object
    # always_xy=True ensures the order is always (longitude, latitude) for geographic CRS
    # and (easting, northing) for projected CRS.
    transformer = pyproj.Transformer.from_crs(src_crs, tgt_crs, always_xy=True)

except pyproj.exceptions.CRSError as e:
    print(f"Error creating CRS or transformer: {e}")
    print("Please ensure the SOURCE_CRS and TARGET_CRS codes are correct and pyproj can find their definitions.")
    exit() # Exit if CRS setup fails

# --- Example Usage ---

# Your sample borehole coordinate (Longitude, Latitude) - order is important for always_xy=True
sample_lon, sample_lat = -122.407051238534, 47.5742507248804

# Perform the transformation
try:
    transformed_x, transformed_y = transformer.transform(sample_lon, sample_lat)

    print(f"Original Lon/Lat: ({sample_lon}, {sample_lat}) in {SOURCE_CRS}")
    print(f"Transformed X/Y:  ({transformed_x:.2f}, {transformed_y:.2f}) in {TARGET_CRS}") # Format to 2 decimal places for readability

except pyproj.exceptions.TransformerError as e:
    print(f"Error transforming point ({sample_lon}, {sample_lat}): {e}")


# --- Applying to a list of borehole coordinates ---

# Example list of points (replace with loading from your CSV/source)
borehole_coords_lonlat = [
    (-122.407051238534, 47.5742507248804),
    (-122.350000000000, 47.6000000000000), # Another example point
    # Add all your borehole (longitude, latitude) tuples here
]

transformed_coords_xy = []

print("\nTransforming list of coordinates:")
for lon, lat in borehole_coords_lonlat:
    try:
        x, y = transformer.transform(lon, lat)
        transformed_coords_xy.append((x, y))
        print(f"  ({lon:.6f}, {lat:.6f}) -> ({x:.2f}, {y:.2f})")
    except pyproj.exceptions.TransformerError as e:
        print(f"  Error transforming point ({lon}, {lat}): {e}")
        transformed_coords_xy.append((None, None)) # Or handle error as needed

# The transformed_coords_xy list now contains your borehole locations
# in NAD83 Washington South (US Survey Feet).
# You would then add these X, Y values as columns to your borehole data table
# for use in your ML model and spatial operations.