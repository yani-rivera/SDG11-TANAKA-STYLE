"""Generate contour lines (in pixel coordinates) with contourpy."""

import numpy as np
import contourpy


def contour_levels(dem, interval):
    lo = np.ceil(np.nanmin(dem) / interval) * interval
    hi = np.floor(np.nanmax(dem) / interval) * interval
    return np.arange(lo, hi + interval / 2, interval)


def contour_lines(dem, interval, min_vertices=6):
    """Return a list of (level, Nx2 array of (col, row)) lines."""
    gen = contourpy.contour_generator(z=dem, line_type="Separate")
    lines = []
    for level in contour_levels(dem, interval):
        for line in gen.lines(level):
            if len(line) >= min_vertices:
                lines.append((float(level), line))
    return lines
