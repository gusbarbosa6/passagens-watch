import logging
from collections import defaultdict
from datetime import date

from .db import DB
from .models import Offer

log = logging.getLogger("watcher")


def months_to_scan(today: date, n: int) -> list[str]:
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _keep(offers: list[Offer], cfg: dict, today: date) -> list[Offer]:
    s = cfg["search"]
    ok = []
    for o in offers:
        if (o.depart - today).days < s["min_lead_days"]:
            continue
        if not (s["trip_min_days"] <= o.trip_days <= s["trip_max_days"]):
            continue
        if o.transfers is not None and o.transfers > s["max_transfers"]:
            continue
        ok.append(o)
    # só as N mais baratas por (origem, destino, mês de saída)
    groups = defaultdict(list)
    for o in ok:
        groups[(o.origin, o.dest, o.depart.strftime("%Y-%m"))].append(o)
    kept = []
    for g in groups.values():
        kept += sorted(g, key=lambda x: x.price)[: s["keep_per_month"]]
    return kept


def collect(provider, db: DB, cfg: dict, today: date) -> dict:
    s, d, o = cfg["search"], cfg["destinations"], cfg["origins"]
    origins = list(o["primary"]) + list(o.get("secondary", {}).keys())
    targets = list(d.get("watch", {}).keys()) + ([None] if d.get("anywhere") else [])
    stats = {"requests": 0, "errors": 0, "offers": 0}
    for origin in origins:
        for month in months_to_scan(today, s["months_ahead"]):
            for dest in targets:
                stats["requests"] += 1
                try:
                    found = provider.search_month(origin, dest, month)
                except Exception as e:  # uma rota falhar não derruba a varredura
                    stats["errors"] += 1
                    log.warning("falha %s→%s %s: %s", origin, dest or "qualquer", month, e)
                    continue
                kept = _keep(found, cfg, today)
                db.upsert_offers(today, kept)
                stats["offers"] += len(kept)
    db.prune(today, s["keep_history_days"])
    return stats
