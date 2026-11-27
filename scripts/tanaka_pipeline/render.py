"""Draw the hypsometric fill, the Tanaka contours, title and credits."""

import textwrap

import matplotlib
matplotlib.use("Agg")  # headless, works on any OS
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm

from .shadows import add_line_shadow, draw_terraces
from .legend import add_color_scale, add_north_star, add_scale_bar


def _plain(text):
    """Show catalog text literally (matplotlib treats $...$ as math markup)."""
    return str(text).replace("$", r"\$")


def _extent(dem, transform):
    h, w = dem.shape
    left, top = transform.c, transform.f
    return left, left + w * transform.a, top + h * transform.e, top


def render_map(dem, transform, segs_map, colors, widths, facing, levels, area, rcfg,
               scfg, azimuth_deg, out_base):
    left, right, bottom, top = _extent(dem, transform)
    aspect = (top - bottom) / (right - left)
    fig_w = rcfg["figure_width_in"]
    header, footer = 1.3, 0.9                         # inches for title and credits
    fig_h = fig_w * aspect + header + footer
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=rcfg["background"])

    map_h = fig_w * aspect / fig_h
    ax = fig.add_axes([0, footer / fig_h, 1, map_h])
    ax.set_axis_off()

    cmap = LinearSegmentedColormap.from_list("hyps", rcfg["fill_colormap"])
    norm = BoundaryNorm(levels, cmap.N, extend="both")
    mode = (scfg or {}).get("mode", "none")

    if mode == "terrace":
        # base colour under the lowest level, then the stepped layers on top
        ax.add_patch(plt.Rectangle((left, bottom), right - left, top - bottom,
                                   facecolor=cmap(0.0), edgecolor="none", zorder=0.5))
        draw_terraces(ax, dem, transform, levels, cmap, norm, azimuth_deg, scfg)
    else:
        ax.imshow(dem, extent=(left, right, bottom, top), cmap=cmap, norm=norm,
                  alpha=rcfg["fill_alpha"], interpolation="nearest", origin="upper",
                  zorder=1)

    if mode == "lines":
        add_line_shadow(ax, segs_map, widths, azimuth_deg, scfg)

    # draw dark lines first, light lines on top
    order = np.argsort(facing > 0, kind="stable")
    lc = LineCollection(segs_map[order], colors=colors[order], linewidths=widths[order],
                        capstyle="round", joinstyle="round", zorder=3)
    ax.add_collection(lc)
    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)
    ax.set_aspect("auto")   # figure already has the map's aspect; fill the frame edge to edge

    lcfg = rcfg.get("color_scale", {"show": True})
    if lcfg.get("show", True):
        add_color_scale(fig, cmap, norm, levels, lcfg, rcfg["title_color"], fig_h, footer)
    bcfg = rcfg.get("scale_bar", {"show": True})
    if bcfg.get("show", True):
        add_scale_bar(ax, (left, right, bottom, top), bcfg, rcfg["title_color"],
                      rcfg["background"])
    ncfg = rcfg.get("north_star", {"show": True})
    if ncfg.get("show", True):
        add_north_star(ax, ncfg, rcfg["title_color"], rcfg["background"], rcfg["background"])

    tc = rcfg["title_color"]
    fig.text(0.5, 1 - 0.55 / fig_h, _plain(area["title"]), ha="center", va="center",
             color=tc, fontsize=30, fontweight="bold", fontfamily="DejaVu Sans")
    fig.text(0.5, 1 - 1.0 / fig_h, _plain(area["subtitle"]), ha="center", va="center",
             color=tc, fontsize=12, alpha=0.85)
    credits = "\n".join(textwrap.wrap(" ".join(rcfg["credits"].split()), 95))
    fig.text(0.02, 0.4 / fig_h, credits, ha="left", va="center", color=tc,
             fontsize=6.5, alpha=0.75)

    written = []
    for fmt in rcfg["formats"]:
        path = f"{out_base}.{fmt}"
        fig.savefig(path, dpi=rcfg["dpi"], facecolor=fig.get_facecolor())
        written.append(path)
    plt.close(fig)
    return written
