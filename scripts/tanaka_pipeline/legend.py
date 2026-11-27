"""Map furniture: elevation colour scale and distance scale bar."""

import numpy as np
from matplotlib.colorbar import ColorbarBase
from matplotlib.patches import Circle, FancyBboxPatch, Polygon


def _nice_ticks(levels, n=5):
    lo, hi = float(levels[0]), float(levels[-1])
    raw = (hi - lo) / max(n - 1, 1)
    mag = 10 ** np.floor(np.log10(raw)) if raw > 0 else 1
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    start = np.ceil(lo / step) * step
    return np.arange(start, hi + step / 2, step)


def add_color_scale(fig, cmap, norm, levels, lcfg, text_color, fig_h, footer_in):
    """Horizontal elevation colour bar in the footer, right side."""
    w, h = lcfg.get("width_frac", 0.32), 0.12 / fig_h
    x = 0.98 - w
    y = (footer_in * 0.62) / fig_h
    cax = fig.add_axes([x, y, w, h])
    cb = ColorbarBase(cax, cmap=cmap, norm=norm, boundaries=levels,
                      orientation="horizontal", spacing="proportional")
    cb.outline.set_visible(False)
    cb.ax.minorticks_off()
    cb.set_ticks(_nice_ticks(levels))
    cb.ax.tick_params(labelsize=7, colors=text_color, length=2, width=0.5)
    cb.ax.xaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    cb.set_label(lcfg.get("label", "Elevation (m)"), color=text_color, fontsize=7.5,
                 labelpad=2)
    cb.ax.xaxis.set_label_position("top")
    return cb


def _nice_length(target_m):
    mag = 10 ** np.floor(np.log10(target_m))
    for m in (5, 2, 1):
        if m * mag <= target_m:
            return m * mag
    return mag


def add_scale_bar(ax, extent, scfg, text_color, box_color):
    """Scale bar in the lower-left corner of the map (map units are metres)."""
    left, right, bottom, top = extent
    width = right - left
    length = _nice_length(width * scfg.get("fraction", 0.2))
    x0 = left + width * 0.04
    y0 = bottom + (top - bottom) * 0.04
    bar_h = (top - bottom) * 0.006
    pad = width * 0.012
    ax.add_patch(FancyBboxPatch((x0 - pad, y0 - pad), length + 2 * pad,
                                bar_h + (top - bottom) * 0.035 + pad,
                                boxstyle=f"round,pad=0,rounding_size={pad}",
                                facecolor=box_color, edgecolor="none", alpha=0.7, zorder=5))
    half = length / 2
    for i, (start, color) in enumerate([(0, text_color), (half, box_color)]):
        ax.add_patch(FancyBboxPatch((x0 + start, y0), half, bar_h, boxstyle="square,pad=0",
                                    facecolor=color, edgecolor=text_color, linewidth=0.5,
                                    zorder=6))
    label = f"{length / 1000:g} km" if length >= 1000 else f"{length:g} m"
    for xv, txt in ((x0, "0"), (x0 + length, label)):
        ax.text(xv, y0 + bar_h * 2, txt, color=text_color, fontsize=7, ha="center",
                va="bottom", zorder=6)


def add_north_star(ax, ncfg, light, dark, box_color):
    """Four-point compass star with N, top-right of the map.
    The map is in UTM, so grid north is used (within ~1 degree of true north here)."""
    size = ncfg.get("size", 0.09)                        # share of map width
    star = ax.inset_axes([0.97 - size, 0.97 - size * 1.35, size, size * 1.35])
    star.set_xlim(-1.3, 1.3)
    star.set_ylim(-1.3, 2.2)
    star.set_aspect("equal")
    star.set_axis_off()
    star.add_patch(Circle((0, 0), 1.25, facecolor=box_color, edgecolor="none", alpha=0.6))
    long, short = 1.0, 0.22
    # each point is split into a lit half and a shaded half, like the contours
    for angle in (0, 90, 180, 270):
        a = np.deg2rad(angle)
        tip = (np.sin(a) * long, np.cos(a) * long)
        left = (np.sin(a - np.pi / 4) * short, np.cos(a - np.pi / 4) * short)
        right = (np.sin(a + np.pi / 4) * short, np.cos(a + np.pi / 4) * short)
        star.add_patch(Polygon([(0, 0), left, tip], closed=True, facecolor=light,
                               edgecolor=light, linewidth=0.4))
        star.add_patch(Polygon([(0, 0), tip, right], closed=True, facecolor=dark,
                               edgecolor=light, linewidth=0.4))
    star.text(0, 1.45, "N", ha="center", va="bottom", color=light, fontsize=9,
              fontweight="bold")
    return star
