"""Run the Tanaka pipeline:  python scripts/run.py --config config/config.yaml"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from tanaka_pipeline.config import load_config, load_area, resolve          # noqa: E402
from tanaka_pipeline.fetch_dem import get_dem                                # noqa: E402
from tanaka_pipeline.preprocess import prepare                               # noqa: E402
from tanaka_pipeline.contours import contour_lines, contour_levels           # noqa: E402
from tanaka_pipeline.tanaka import segment_facing, pixel_to_map, style_segments  # noqa: E402
from tanaka_pipeline.render import render_map                                # noqa: E402
from tanaka_pipeline.interval import resolve_interval                         # noqa: E402
from tanaka_pipeline.provenance import write_provenance, append_run_log      # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(PROJECT_ROOT / "config" / "config.yaml"))
    ap.add_argument("--area", help="area_id from the catalog (overrides area_id in the config)")
    ap.add_argument("--refresh-dem", action="store_true",
                    help="download the DEM again even if it is cached")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.area:
        cfg["area_id"] = args.area
    area = load_area(cfg)
    run_id = f"{cfg['area_id']}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    run_dir = resolve(cfg, cfg["output"]["dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] DEM ({cfg['dem']['source']})")
    dem_path, dem_sources, dem_cache = get_dem(cfg, area, args.refresh_dem)

    print("[2/5] Reproject, fill, smooth")
    dem, transform, crs = prepare(dem_path, area, cfg)

    print("[3/5] Contours")
    interval, interval_source, interval_details = resolve_interval(cfg, area, dem)
    print(f"      interval {interval:g} m ({interval_source})")
    lines = contour_lines(dem, interval, cfg["contours"]["min_vertices"])

    print("[4/5] Tanaka shading")
    segs_px, facing = segment_facing(dem, lines, cfg["tanaka"]["light_azimuth_deg"])
    segs_map = pixel_to_map(segs_px, transform)
    colors, widths = style_segments(facing, cfg["tanaka"])

    print("[5/5] Render")
    outputs = render_map(dem, transform, segs_map, colors, widths, facing,
                         contour_levels(dem, interval), area, cfg["render"],
                         cfg.get("shadow"), cfg["tanaka"]["light_azimuth_deg"],
                         run_dir / f"tanaka_{cfg['area_id']}")

    stats = {
        "dem_cache": dem_cache,
        "crs": crs,
        "dem_shape": list(dem.shape),
        "elev_min_m": float(dem.min()),
        "elev_max_m": float(dem.max()),
        "interval_m": interval,
        "interval_source": interval_source,
        **interval_details,
        "n_contour_lines": len(lines),
        "n_segments": int(len(facing)),
    }
    record = write_provenance(cfg, area, run_id, run_dir, dem_path, dem_sources,
                              [str(p) for p in outputs], stats)
    append_run_log(resolve(cfg, cfg["output"]["run_log"]), record)
    print("Done:", *outputs, sep="\n  ")


if __name__ == "__main__":
    main()
