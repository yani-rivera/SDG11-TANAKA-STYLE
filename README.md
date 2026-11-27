# Tanaka pipeline: illuminated contours in pure Python

Builds a Tanaka-style (illuminated contour) map from a DEM. It needs no GIS software and works the same on Windows, macOS and Linux.

Each contour segment is coloured by which way it faces the light: light where the slope faces the light source, dark where it faces away. Width grows with how directly the slope faces towards or away from the light.

## Install

### Recommended: conda environment (Windows, macOS, Linux)

The pipeline runs in its own conda environment, built only from **conda-forge**. That keeps it separate from your `base` environment and other projects, and conda-forge ships rasterio/GDAL ready to use on every OS.

You need [Miniforge](https://github.com/conda-forge/miniforge) (or Anaconda/Miniconda). Then, from the project folder:

```bash
conda env create -f environment.yml
conda activate tanaka
```

Check that it works:

```bash
python -c "import rasterio, scipy, matplotlib, contourpy, yaml; print('ok')"
```

To update the environment after `environment.yml` changes:

```bash
conda env update -f environment.yml --prune
```

To remove it:

```bash
conda deactivate
conda env remove -n tanaka
```

> **Don't mix pip into this environment.** Installing or upgrading packages with `pip` on top of conda packages can leave SciPy, NumPy or GDAL with mismatched compiled parts (for example `ImportError: cannot import name '_spropack'`). If that happens, remove the environment and create it again with the commands above.

### Recording the exact versions

`environment.yml` sets minimum versions. To record the exact versions you ran with, for a release or a paper:

```bash
conda env export --no-builds > environment.lock.yml
```

Others can recreate that exact environment with `conda env create -f environment.lock.yml`. Each run's `provenance.json` also records the package versions it used.

### Alternative: pip

If you don't use conda, use a fresh virtual environment (not your system Python):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Activate the environment first (`conda activate tanaka`), then:

```bash
python scripts/run.py                      # uses config/config.yaml and its area_id
python scripts/run.py --area SPS           # another city from catalogs/areas.csv
python scripts/run.py --refresh-dem        # download the DEM again
```

With `dem.source: copernicus`, the pipeline reads only the bounding-box window of the Copernicus GLO-30 tiles over HTTPS and caches it in `data/raw/`. You can also use your own DEM: set `dem.source: local` and `dem.local_path`.

### Offline test

```bash
python tests/make_synthetic_dem.py data/raw/synthetic_dem.tif
python scripts/run.py --config tests/config_synthetic.yaml
```

## Layout

```
README.md
environment.yml           conda environment (conda-forge)
requirements.txt          pip alternative
catalogs/areas.csv        area_id, title, subtitle, bbox (WGS84), UTM EPSG, optional interval_m (utf-8-sig)
config/config.yaml        all parameters (no place names)
data/raw/                 DEM cache (not versioned)
output/<run_id>/          map + provenance.json; output/run_log.csv (not versioned)
scripts/run.py            orchestrates the steps
scripts/tanaka_pipeline/
  config.py               config + catalog loading
  fetch_dem.py            Copernicus GLO-30 window or local GeoTIFF
  preprocess.py           reproject to UTM, fill gaps, Gaussian smoothing
  contours.py             contour lines with contourpy
  tanaka.py               aspect vs light -> colour and width per segment
  render.py               hypsometric fill + Tanaka lines + title/credits
  interval.py             contour interval: catalog > config > auto (from typical slope)
  shadows.py              cast shadows: under the lines, or stepped terraces
  provenance.py           provenance.json per run + output/run_log.csv (utf-8-sig)
tests/make_synthetic_dem.py
```

## Add a city

Every place lives in `catalogs/areas.csv`, one row per area. The code and the config don't change.

**1. Add a row** (keep the file saved as UTF-8):

```csv
area_id,title,subtitle,west,south,east,north,utm_epsg,interval_m
CMY,COMAYAGUA,Honduras · illuminated contours,-87.76,14.36,-87.54,14.56,32616,
```

| Column | What to put |
|---|---|
| `area_id` | Short code used in file names: letters, digits, `-` and `_` only (e.g. `CMY`). |
| `title`, `subtitle` | Text printed at the top of the map. |
| `west, south, east, north` | Bounding box in decimal degrees (WGS84). West of Greenwich and south of the equator are negative. West must be smaller than east, south smaller than north. |
| `utm_epsg` | UTM zone of the area (see below). |
| `interval_m` | Optional contour interval in metres for this area. Leave empty to use the config value or `auto`. |

**2. Find the UTM zone.** Zone = `floor((longitude + 180) / 6) + 1`, using the centre longitude.
EPSG = `32600 + zone` in the northern hemisphere, `32700 + zone` in the southern.
For example, Honduras (≈ −87°) is zone 16 → `32616`, and Guatemala City (≈ −90.5°) is zone 15 → `32615`.

**3. Check the box** before running. In QGIS: *Vector → Research Tools → Create Layer from Extent* and enter `west,east,south,north [EPSG:4326]`. Make sure it covers the terrain you want, not only the city limits; for Tanaka, the surrounding hills are what make the map.

**4. Run it:**

```bash
python scripts/run.py --area CMY
```

With `dem.source: copernicus`, the pipeline works out which 1° Copernicus tiles the box needs, downloads only the window inside the box, and caches it under a name that includes the box. A box crossing a whole degree of latitude or longitude needs more than one tile, which is handled automatically. With `dem.source: local`, your DEM file must cover the whole box.

**5. Tune if needed.** Flat terrain (valleys, plateaus) needs a smaller interval and steep terrain a bigger one. Set `interval_m` in the catalog row for that city, or use `interval_m: auto` in the config.

## Provenance

Every run writes `output/<run_id>/provenance.json`. It records the script version, git commit, Python and package versions, the full config and its SHA-256, the area row, the DEM source URLs, the DEM file hash and the outputs. Each run also appends one row to `output/run_log.csv`.

## Tuning

| Parameter | Effect |
|---|---|
| `contours.interval_m` | Line density in metres, or `auto`. Flat terrain needs a smaller interval, steep terrain a bigger one. A value in the catalog's `interval_m` column overrides it for that city. |
| `contours.auto.target_spacing_mm` | With `auto`: desired gap between lines on the printed map. Raise it for an airier map. |
| `preprocess.smooth_sigma_px` | More smoothing gives calmer, cleaner lines. |
| `tanaka.light_azimuth_deg` | 315 (NW) is the classic choice. Try 225 or 270 to change how the ridges read. |
| `tanaka.width_min/max` | Contrast of the effect. |
| `render.fill_colormap` | Hypsometric tint, low to high. |
| `shadow.mode` | `none`, `lines` (drop shadow under every contour) or `terrace` (stepped paper layers; slower). |
| `shadow.layers` | Stack several shadows, like QGIS draw effects: `color`, `alpha`, `distance_pt`, `softness_steps`, `width_scale`. Shadows fall away from the light. |

## Data credit

Copernicus DEM GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA.
