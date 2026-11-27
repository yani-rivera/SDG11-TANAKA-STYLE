"""Cast shadows that strengthen the Tanaka effect.

Two modes (config `shadow.mode`):
  lines    - a soft drop shadow under every contour line
  terrace  - stepped "paper layers": each elevation band casts a shadow on the one below
Several shadow layers can be stacked (config `shadow.layers`), like QGIS draw effects,
e.g. a tight dark shadow plus a wide soft one. Each layer: color, alpha, distance_pt,
softness_steps, width_scale. Shadows always fall away from the light.
"""

import contourpy
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.transforms import offset_copy


def shadow_offset(azimuth_deg, distance_pt):
    """(dx, dy) in points, pointing away from the light."""
    a = np.deg2rad(azimuth_deg)
    return -np.sin(a) * distance_pt, -np.cos(a) * distance_pt


def _soft_steps(scfg):
    """Offsets and alphas for a soft shadow built from stacked copies."""
    n = max(1, int(scfg.get("softness_steps", 4)))
    fractions = np.linspace(1.0 / n, 1.0, n)
    alpha_each = scfg["alpha"] / n
    return fractions, alpha_each


def shadow_layers(scfg):
    """List of shadow layer dicts (accepts the old single-shadow form too)."""
    if not scfg:
        return []
    if "layers" in scfg:
        return list(scfg["layers"])
    return [scfg]


def add_line_shadow(ax, segs_map, widths, azimuth_deg, scfg):
    """Draw stacked, offset copies of the contour lines underneath them.
    Layers are drawn in reverse order so the first layer ends up closest to the lines."""
    fig = ax.figure
    for layer in reversed(shadow_layers(scfg)):
        dx, dy = shadow_offset(azimuth_deg, layer["distance_pt"])
        fractions, alpha_each = _soft_steps(layer)
        for f in fractions:
            tr = offset_copy(ax.transData, fig=fig, x=dx * f, y=dy * f, units="points")
            ax.add_collection(LineCollection(
                segs_map, colors=layer["color"], alpha=alpha_each,
                linewidths=widths * layer.get("width_scale", 2.0),
                capstyle="round", joinstyle="round", transform=tr, zorder=2))


def _level_path(gen, level, top, transform):
    """Compound path (map coords) of the area at or above `level`."""
    points, codes = gen.filled(level, top)
    if not points:
        return None
    verts = np.concatenate(points)
    verts = np.column_stack([
        transform.c + (verts[:, 0] + 0.5) * transform.a,
        transform.f + (verts[:, 1] + 0.5) * transform.e,
    ])
    return Path(verts, np.concatenate(codes))


def draw_terraces(ax, dem, transform, levels, cmap, norm, azimuth_deg, scfg):
    """Stepped paper layers: for each level (low to high) draw its shadow, then its fill.
    Each layer's shadow falls on the layers below it."""
    fig = ax.figure
    gen = contourpy.contour_generator(z=dem, fill_type="OuterCode")
    top = float(np.nanmax(dem)) + 1.0
    layers = list(reversed(shadow_layers(scfg)))
    step = levels[1] - levels[0] if len(levels) > 1 else 1.0
    for level in levels:
        path = _level_path(gen, level, top, transform)
        if path is None:
            continue
        for layer in layers:
            dx, dy = shadow_offset(azimuth_deg, layer["distance_pt"])
            fractions, alpha_each = _soft_steps(layer)
            for f in fractions:
                tr = offset_copy(ax.transData, fig=fig, x=dx * f, y=dy * f, units="points")
                ax.add_patch(PathPatch(path, facecolor=layer["color"], edgecolor="none",
                                       alpha=alpha_each, transform=tr, zorder=1))
        ax.add_patch(PathPatch(path, facecolor=cmap(norm(level + step / 2)),
                               edgecolor="none", zorder=1))
    # same zorder for every patch: matplotlib keeps insertion order, so each level's
    # shadow lands on top of the levels below it; contour lines (zorder 3) stay on top
