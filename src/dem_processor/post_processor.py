import numpy as np
from typing import List

def convert_aspect_degrees_to_radians(aspect_degrees: np.ndarray | List[float]) -> np.ndarray:
    """
    Converts an iterable of aspect angles in degrees to radians.

    Args:
        aspect_degrees: An iterable of aspect angles in degrees.

    Returns:
        A numpy array of aspect angles in radians.
    """
    return np.radians(aspect_degrees)

def extract_aspect_sin_cos_components(aspect_radians: np.ndarray) -> np.ndarray:
    """
    Extracts the sin and cos components from an array of aspect angles in radians.

    Args:
        aspect_radians: An array of aspect angles in radians.

    Returns:
        A numpy array containing the sin and cos components of the aspect angles.
    """
    return np.sin(aspect_radians), np.cos(aspect_radians)
