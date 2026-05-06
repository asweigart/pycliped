import json
import os
import sys
from pathlib import Path


def config_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / "pycliped" / "config.json"
    return Path(os.path.expanduser("~/.config/pycliped/config.json"))


def default_config() -> dict:
    from .presets import PRESETS, DEFAULT_PRESET

    return {
        "enabled": True,
        "preset": DEFAULT_PRESET,
        "code": PRESETS[DEFAULT_PRESET],
        "poll_interval_ms": 500,
        "geometry": None,
        "preview_visible": False,
        "history_visible": False,
        "history": [],
    }


def load() -> dict:
    cfg = default_config()
    path = config_path()
    if not path.exists():
        return cfg
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return cfg
    if isinstance(data, dict):
        cfg.update({k: v for k, v in data.items() if k in cfg})
    return cfg


def save(cfg: dict) -> None:
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass
