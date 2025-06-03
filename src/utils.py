import pandas as pd
import pyproj

def transform_crs(
        df: pd.DataFrame,
        source_crs: str,
        target_crs: str,
        longitude_column: str = 'LONGITUDE',
        latitude_column: str = 'LATITUDE'
        ) -> pd.DataFrame:
    """
    Transform the coordinates in a DataFrame from one CRS to another.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the coordinates to be transformed.
    source_crs : str
        The source coordinate reference system (CRS) of the coordinates.
    target_crs : str
        The target coordinate reference system (CRS) of the coordinates.
    longitude_column : str, optional
        The column name of the longitude coordinates. Defaults to 'LONGITUDE'.
    latitude_column : str, optional
        The column name of the latitude coordinates. Defaults to 'LATITUDE'.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with the transformed coordinates.
    """
    src_crs_pyproj = pyproj.CRS(source_crs)
    tgt_crs_pyproj = pyproj.CRS(target_crs)

    # Create a transformer object
    # always_xy=True ensures the order is always (longitude, latitude) for geographic CRS
    # and (easting, northing) for projected CRS.
    transformer = pyproj.Transformer.from_crs(src_crs_pyproj, tgt_crs_pyproj, always_xy=True)

    transformed_lat = []
    transformed_long = []
    for _, row in df.iterrows():
        x = row[longitude_column]
        y = row[latitude_column]
        transformed_x, transformed_y = transformer.transform(x, y)
        if transformed_x is None or transformed_y is None:
            print(f"Error transforming point ({x}, {y})")
            continue
        transformed_long.append(transformed_x)
        transformed_lat.append(transformed_y)

    cleaned_target_crs = ''.join(char for char in target_crs if char.isalnum())
    new_longitude_column = cleaned_target_crs + '_LONGITUDE'
    new_latitude_column = cleaned_target_crs + '_LATITUDE'

    df[new_longitude_column] = transformed_long
    df[new_latitude_column] = transformed_lat

    return df