"""Tanaka shading: colour and width of each contour segment from its aspect."""

import numpy as np
from scipy import ndimage


def light_vector(azimuth_deg):
    """Unit vector (east, north) pointing towards the light source."""
    a = np.deg2rad(azimuth_deg)
    return np.sin(a), np.cos(a)


def segment_facing(dem, lines, azimuth_deg):
    """For every contour segment return its midpoint (col,row) and a facing value.

    facing = +1 when the slope faces the light directly, -1 when it faces away.
    Rows grow southwards, so the north gradient is minus the row gradient.
    """
    d_row, d_col = np.gradient(dem)
    lx, ly = light_vector(azimuth_deg)

    seg_list, mids = [], []
    for _, line in lines:
        a, b = line[:-1], line[1:]
        seg_list.append(np.stack([a, b], axis=1))   # (n, 2, 2) in (col, row)
        mids.append((a + b) / 2)
    if not seg_list:
        return np.empty((0, 2, 2)), np.empty(0)
    segs = np.concatenate(seg_list)
    mid = np.concatenate(mids)

    coords = [mid[:, 1], mid[:, 0]]                # (row, col) for map_coordinates
    g_east = ndimage.map_coordinates(d_col, coords, order=1, mode="nearest")
    g_north = -ndimage.map_coordinates(d_row, coords, order=1, mode="nearest")
    norm = np.hypot(g_east, g_north)
    norm[norm == 0] = 1.0
    # downhill direction is minus the gradient; a slope faces the light
    # when its downhill direction points towards the light
    facing = -(g_east * lx + g_north * ly) / norm
    return segs, facing


def pixel_to_map(segs, transform):
    """Convert (col, row) pixel-index coordinates to map coordinates (pixel centres)."""
    cols = segs[..., 0] + 0.5
    rows = segs[..., 1] + 0.5
    x = transform.c + cols * transform.a + rows * transform.b
    y = transform.f + cols * transform.d + rows * transform.e
    return np.stack([x, y], axis=-1)


def style_segments(facing, tcfg):
    """Colours and widths for each segment."""
    colors = np.where(facing > 0, tcfg["light_color"], tcfg["dark_color"])
    widths = tcfg["width_min"] + (tcfg["width_max"] - tcfg["width_min"]) * np.abs(facing)
    return colors, widths
