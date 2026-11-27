"""Reproject the DEM to UTM (metres), clip to the area, fill gaps and smooth."""

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.transform import from_origin
from scipy import ndimage


def to_utm(dem_path, area, resolution_m):
    """Return (array, affine) in the area's UTM CRS, clipped to its bbox."""
    dst_crs = f"EPSG:{area['utm_epsg']}"
    with rasterio.open(dem_path) as src:
        left, bottom, right, top = transform_bounds("EPSG:4326", dst_crs,
                                                    area["west"], area["south"],
                                                    area["east"], area["north"])
        width = int(np.ceil((right - left) / resolution_m))
        height = int(np.ceil((top - bottom) / resolution_m))
        transform = from_origin(left, top, resolution_m, resolution_m)
        out = np.full((height, width), np.nan, dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return out, transform, dst_crs


def fill_nodata(arr):
    """Fill NaNs with the nearest valid value (keeps contours from breaking)."""
    mask = np.isnan(arr)
    if not mask.any():
        return arr
    if mask.all():
        raise ValueError("DEM window has no valid data - check the bounding box")
    idx = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
    return arr[tuple(idx)]


def smooth(arr, sigma_px):
    return ndimage.gaussian_filter(arr, sigma_px) if sigma_px and sigma_px > 0 else arr


def prepare(dem_path, area, cfg):
    arr, transform, crs = to_utm(dem_path, area, cfg["dem"]["resolution_m"])
    arr = fill_nodata(arr)
    arr = smooth(arr, cfg["preprocess"]["smooth_sigma_px"])
    return arr, transform, crs
