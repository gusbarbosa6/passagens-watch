import statistics
from collections import defaultdict
from datetime import date, timedelta

from .db import DB
from .models import Deal, Offer

BUCKETS = [(0, 30), (30, 60), (60, 120), (120, 10_000)]


def bucket(lead: int) -> tuple[int, int]:
    for lo, hi in BUCKETS:
        if lo <= lead < hi:
            return lo, hi
    return BUCKETS[-1]


def row_to_offer(r) -> Offer:
    return Offer(r["origin"], r["dest"], r["dest_airport"] or r["dest"], date.fromisoformat(r["depart"]),
                 date.fromisoformat(r["ret"]), r["price"], r["transfers"], r["airline"] or "",
                 r["link"] or "", r["source"] or "")


def _percentile(sorted_vals, q):
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def find_deals(db: DB, cfg: dict, today: date) -> list[Deal]:
    a, o = cfg["alerts"], cfg["origins"]
    targets = {k: v for k, v in cfg["destinations"].get("watch", {}).items()}
    secondary = o.get("secondary", {})
    offers = [row_to_offer(r) for r in db.offers_for_day(today)]

    by_route = defaultdict(list)
    for x in offers:
        by_route[(x.origin, x.dest)].append(x.price)
    best_primary = {}
    for x in offers:
        if x.origin in o["primary"]:
            best_primary[x.dest] = min(best_primary.get(x.dest, 1e18), x.price)

    since = today - timedelta(days=a["history_window_days"])
    deals = []
    for x in offers:
        if x.origin in secondary:  # aeroporto distante: só se for bem mais barato
            ref = best_primary.get(x.dest)
            if ref is None or x.price > (1 - secondary[x.origin]) * ref:
                continue
        reasons, kind, ref_price, discount = [], None, None, 0.0

        target = targets.get(x.dest) or targets.get(x.dest_airport) or 0
        if target and x.price <= target:
            reasons.append(f"abaixo da sua meta de R$ {target:,.0f}".replace(",", "."))
            kind, ref_price, discount = "meta", float(target), 1 - x.price / target

        lo, hi = bucket((x.depart - today).days)
        hist, ndays = db.history(x.origin, x.dest, lo, hi, since, today)
        if len(hist) >= a["min_history_rows"] and ndays >= a["min_history_days"]:
            hist.sort()
            med, p = statistics.median(hist), _percentile(hist, a["percentile"])
            if x.price <= p and x.price <= a["below_median"] * med:
                d = 1 - x.price / med
                reasons.append(f"{d:.0%} abaixo da mediana das ofertas recentes (R$ {med:,.0f})".replace(",", "."))
                if kind != "meta" or d > discount:
                    kind, ref_price, discount = ("meta" if kind == "meta" else "historico"), med, max(d, discount)
        else:
            cross = by_route[(x.origin, x.dest)]
            if len(cross) >= 6:
                med = statistics.median(cross)
                if x.price <= a["cross_section_ratio"] * med:
                    d = 1 - x.price / med
                    reasons.append(f"{d:.0%} abaixo da mediana de hoje (histórico ainda curto)")
                    if kind is None:
                        kind, ref_price, discount = "varredura", med, d

        cap = a["discovery_max_price"]
        if cap and x.dest not in targets and x.dest_airport not in targets and x.price <= cap:
            reasons.append(f"destino fora da lista por menos de R$ {cap:,.0f}".replace(",", "."))
            kind = kind or "descoberta"

        if reasons:
            deals.append(Deal(x, reasons, ref_price, discount, kind or "descoberta"))

    # uma oferta por (origem, destino): a mais barata
    best = {}
    for d in deals:
        k = (d.offer.origin, d.offer.dest)
        if k not in best or d.offer.price < best[k].offer.price:
            best[k] = d
    return sorted(best.values(), key=lambda d: (-d.discount, d.offer.price))


def new_alerts(db: DB, deals: list[Deal], cfg: dict, today: date) -> list[Deal]:
    """Filtra o que já foi avisado (evita repetir o mesmo alerta todo dia)."""
    a = cfg["alerts"]
    fresh = []
    for d in deals:
        key = f"{d.offer.origin}-{d.offer.dest}-{d.offer.depart}-{d.offer.ret}"
        prev = db.get_alert(key)
        if prev is not None:
            age = (today - date.fromisoformat(prev["alerted_at"])).days
            if age < a["repeat_after_days"] and d.offer.price > prev["price"] * 0.95:
                continue
        fresh.append(d)
    return fresh[: a["max_alerts_per_run"]]


def mark_alerted(db: DB, deals: list[Deal], today: date):
    for d in deals:
        o = d.offer
        db.put_alert(f"{o.origin}-{o.dest}-{o.depart}-{o.ret}", o.price, today)


def window_summary(db: DB, today: date, windows=(14, 30, 60, 90)):
    """Quanto custa sair logo: menor preço e mediana por destino, por janela de saída."""
    offers = [row_to_offer(r) for r in db.offers_for_day(today)]
    by_dest = defaultdict(list)
    for x in offers:
        by_dest[x.dest].append(x)
    out = []
    for dest, xs in by_dest.items():
        row = {"dest": dest, "windows": {}}
        for w in windows:
            sel = [x for x in xs if (x.depart - today).days <= w]
            if sel:
                best = min(sel, key=lambda x: x.price)
                row["windows"][w] = {"best": best, "median": statistics.median(x.price for x in sel)}
        if row["windows"]:
            out.append(row)
    key_w = windows[1]

    def sort_key(r):
        w = r["windows"].get(key_w)
        return w["best"].price if w else 1e18

    out.sort(key=sort_key)
    return out
