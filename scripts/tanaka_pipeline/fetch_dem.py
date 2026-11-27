"""Get the DEM for the area: Copernicus GLO-30 over HTTPS, or a local GeoTIFF."""

import math
from pathlib import Path

import rasterio
import rasterio.errors
from rasterio.merge import merge

from .config import resolve


def copernicus_tile_urls(area, template):
    """URLs of the 1x1 degree Copernicus tiles that cover the bounding box."""
    urls = []
    for lat in range(math.floor(area["south"]), math.ceil(area["north"])):
        for lon in range(math.floor(area["west"]), math.ceil(area["east"])):
            lat_s = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            lon_s = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
            urls.append(template.format(lat=lat_s, lon=lon_s))
    return urls


def cache_path(cfg, area):
    """Cache file name carries the area and its bbox, so a new bbox means a new download
    and an unchanged bbox always reuses the file."""
    cache_dir = resolve(cfg, cfg["dem"]["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    bbox = f"{area['west']:.4f}_{area['south']:.4f}_{area['east']:.4f}_{area['north']:.4f}"
    return cache_dir / f"copernicus_glo30_{cfg['area_id']}_{bbox}.tif"


def fetch_copernicus(cfg, area, refresh=False):
    """Read only the bbox window from the tiles and cache it as a GeoTIFF.

    Returns (path, urls, cache_status) where cache_status is "hit" or "downloaded".
    """
    out = cache_path(cfg, area)
    urls = copernicus_tile_urls(area, cfg["dem"]["copernicus_url_template"])
    if not all(u.startswith("https://") for u in urls):
        raise ValueError("dem.copernicus_url_template must use https://")
    if out.exists() and not refresh:
        print(f"      using cached DEM: {out}")
        return out, urls, "hit"

    print(f"      downloading {len(urls)} tile window(s) -> {out}")
    bounds = (area["west"], area["south"], area["east"], area["north"])
    try:
        sources = [rasterio.open(u) for u in urls]
    except rasterio.errors.RasterioIOError as e:
        raise RuntimeError(
            "Could not read Copernicus tiles over HTTPS. Check your connection, "
            "or download the tile and set dem.source: local in the config.\n"
            f"Tiles: {urls}") from e
    try:
        mosaic, transform = merge(sources, bounds=bounds)
        profile = sources[0].profile.copy()
    finally:
        for s in sources:
            s.close()
    profile.update(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2],
                   transform=transform, compress="deflate", tiled=False,
                   blockxsize=None, blockysize=None)
    tmp = out.with_suffix(".part.tif")          # write to a temp file, then rename,
    try:                                        # so a failed download never leaves
        with rasterio.open(tmp, "w", **{k: v for k, v in profile.items() if v is not None}) as dst:
            dst.write(mosaic)                   # a broken file in the cache
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)
    return out, urls, "downloaded"


def get_dem(cfg, area, refresh=False):
    """Return (path_to_dem, list_of_sources, cache_status) per cfg['dem']['source']."""
    source = cfg["dem"]["source"]
    if source == "copernicus":
        return fetch_copernicus(cfg, area, refresh)
    if source == "local":
        path = resolve(cfg, cfg["dem"]["local_path"])
        if not Path(path).exists():
            raise FileNotFoundError(path)
        print(f"      using local DEM: {path}")
        return path, [str(path)], "local"
    raise ValueError(f"unknown dem.source {source!r}")
