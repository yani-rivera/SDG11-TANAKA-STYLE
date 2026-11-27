"""Load the YAML config and the area catalog."""

import csv
import re
from pathlib import Path

import yaml


def load_config(path):
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(path.resolve())
    cfg["_project_root"] = str(path.resolve().parent.parent)
    return cfg


def resolve(cfg, relative):
    """Resolve a config path relative to the project root."""
    p = Path(relative)
    return p if p.is_absolute() else Path(cfg["_project_root"]) / p


AREA_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def validate_area(row):
    """Reject values that could break paths or projections (area_id is used in file names)."""
    if not AREA_ID_RE.match(row["area_id"]):
        raise ValueError(f"area_id {row['area_id']!r}: use only letters, digits, - and _")
    if not (-180 <= row["west"] < row["east"] <= 180 and -90 <= row["south"] < row["north"] <= 90):
        raise ValueError(f"area {row['area_id']}: bounding box is not valid WGS84 (west<east, south<north)")
    if not (32601 <= row["utm_epsg"] <= 32660 or 32701 <= row["utm_epsg"] <= 32760):
        raise ValueError(f"area {row['area_id']}: utm_epsg {row['utm_epsg']} is not a WGS84 UTM zone")
    if row.get("interval_m") is not None and not row["interval_m"] > 0:
        raise ValueError(f"area {row['area_id']}: interval_m must be positive")
    return row


def load_area(cfg):
    """Return the catalog row for cfg['area_id'], with numeric fields cast and checked."""
    if not AREA_ID_RE.match(str(cfg["area_id"])):
        raise ValueError(f"area_id {cfg['area_id']!r}: use only letters, digits, - and _")
    catalog = resolve(cfg, cfg["areas_catalog"])
    with catalog.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["area_id"] == cfg["area_id"]:
                for k in ("west", "south", "east", "north"):
                    row[k] = float(row[k])
                row["utm_epsg"] = int(row["utm_epsg"])
                iv = (row.get("interval_m") or "").strip()
                row["interval_m"] = float(iv) if iv else None
                return validate_area(row)
    raise KeyError(f"area_id {cfg['area_id']!r} not found in {catalog}")
