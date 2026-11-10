import tomllib
from pathlib import Path

DEFAULTS = {
    "search": {
        "source": "travelpayouts", "currency": "brl", "market": "br",
        "months_ahead": 6, "min_lead_days": 3, "trip_min_days": 5,
        "trip_max_days": 15, "max_transfers": 1, "keep_per_month": 8,
        "keep_history_days": 120,
    },
    "origins": {"primary": ["GRU", "CGH"], "secondary": {}},
    "destinations": {"anywhere": True, "watch": {}},
    "alerts": {
        "history_window_days": 90, "min_history_rows": 40, "min_history_days": 5,
        "percentile": 0.20, "below_median": 0.85, "cross_section_ratio": 0.75,
        "discovery_max_price": 0, "max_alerts_per_run": 10, "repeat_after_days": 7,
    },
}


def load(path="config.toml") -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    p = Path(path)
    if p.exists():
        with p.open("rb") as f:
            user = tomllib.load(f)
        for section, values in user.items():
            if isinstance(values, dict) and isinstance(cfg.get(section), dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
    return cfg
