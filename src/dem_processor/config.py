# Filenames for saving the index files
INDEX_FILE_PREFIX = "raster_spatial_index" # Creates raster_spatial_index.idx and .dat
INFO_LIST_FILE = "raster_info_list.pkl"   # File to save raster metadata list

# List of directories containing your raster files (DEM, Slope, TWI, etc.)
RASTER_DIRS = ["../../../soilense_data/DEM/washington_10meter_dem_tiles/reprojected_dems_wa_south_ft"]

RASTER_TYPE_PATTERNS = {
    'TIF': '*.tif',
    'DEM': '*.dem',
}