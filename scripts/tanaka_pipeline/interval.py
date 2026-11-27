"""Choose the contour interval: catalog value > config number > automatic.

Automatic: on the printed map, lines should sit about `target_spacing_mm` apart on a
typical slope. Ground spacing between contours = interval / slope, so
    interval = slope_typical * ground_spacing_for_target_mm
rounded to a clean value from `nice_values`.
"""

import numpy as np


def typical_slope(dem, resolution_m, percentile):
    """Slope (rise/run) at the given percentile, ignoring almost-flat cells."""
    d_row, d_col = np.gradient(dem, resolution_m)
    slope = np.hypot(d_row, d_col)
    moving = slope[slope > 0.01]          # flat floors would drag the value to zero
    if moving.size == 0:
        return float(np.percentile(slope, percentile))
    return float(np.percentile(moving, percentile))


def nearest_nice(value, nice_values):
    nice = np.asarray(sorted(nice_values), dtype=float)
    return float(nice[np.argmin(np.abs(np.log(nice) - np.log(max(value, 1e-6))))])


def auto_interval(dem, resolution_m, figure_width_in, acfg):
    map_width_m = dem.shape[1] * resolution_m
    metres_per_mm = map_width_m / (figure_width_in * 25.4)
    ground_spacing_m = acfg["target_spacing_mm"] * metres_per_mm
    slope = typical_slope(dem, resolution_m, acfg["slope_percentile"])
    raw = slope * ground_spacing_m
    return nearest_nice(raw, acfg["nice_values"]), {"slope_typical": round(slope, 4),
                                                    "interval_raw_m": round(raw, 2)}


def resolve_interval(cfg, area, dem):
    """Return (interval_m, source, details)."""
    if area.get("interval_m"):
        return float(area["interval_m"]), "catalog", {}
    value = cfg["contours"]["interval_m"]
    if str(value).lower() != "auto":
        return float(value), "config", {}
    interval, details = auto_interval(dem, cfg["dem"]["resolution_m"],
                                      cfg["render"]["figure_width_in"],
                                      cfg["contours"]["auto"])
    return interval, "auto", details
