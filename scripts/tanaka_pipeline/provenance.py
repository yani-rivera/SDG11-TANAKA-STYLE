"""Record provenance for every run: script version, config, sources, packages."""

import csv
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

from . import __version__

PACKAGES = ["numpy", "scipy", "rasterio", "matplotlib", "contourpy", "PyYAML"]


def _git_commit(root):
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def _pkg_versions():
    out = {}
    for p in PACKAGES:
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            out[p] = None
    return out


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path, root):
    """Path relative to the project root, so provenance files don't expose local user paths."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name          # outside the project: keep only the file name


def write_provenance(cfg, area, run_id, run_dir, dem_path, dem_sources, outputs, stats):
    root = cfg["_project_root"]
    config_text = Path(cfg["_config_path"]).read_bytes()
    record = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline": "tanaka_pipeline",
        "script_version": __version__,
        "git_commit": _git_commit(cfg["_project_root"]),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "packages": _pkg_versions(),
        "config_path": _rel(cfg["_config_path"], root),
        "config_sha256": hashlib.sha256(config_text).hexdigest(),
        "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "area": area,
        "dem_sources": [u if u.startswith("https://") else _rel(u, root) for u in dem_sources],
        "dem_file": _rel(dem_path, root),
        "dem_sha256": file_sha256(dem_path),
        "outputs": [_rel(o, root) for o in outputs],
        "stats": stats,
    }
    with open(Path(run_dir) / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return record


def append_run_log(log_path, record):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": record["run_id"],
        "timestamp_utc": record["timestamp_utc"],
        "script_version": record["script_version"],
        "git_commit": record["git_commit"] or "",
        "area_id": record["area"]["area_id"],
        "config_sha256": record["config_sha256"],
        "dem_sha256": record["dem_sha256"],
        "n_segments": record["stats"]["n_segments"],
        "outputs": ";".join(record["outputs"]),
    }
    new = not log_path.exists()
    with log_path.open("a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
