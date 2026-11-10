import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta

from . import config as config_mod
from .analyze import find_deals, mark_alerted, new_alerts
from .collect import collect
from .dashboard import render
from .db import DB
from .notify import format_message, send_telegram
from .providers.mock import MockProvider
from .providers.travelpayouts import TravelpayoutsProvider

log = logging.getLogger("watcher")


def make_provider(cfg, source=None, as_of=None):
    source = source or cfg["search"]["source"]
    if source == "mock":
        return MockProvider(as_of)
    s = cfg["search"]
    return TravelpayoutsProvider(os.getenv("TRAVELPAYOUTS_TOKEN", ""), s["currency"], s["market"])


def run(cfg, db, source=None, notify=True, today=None):
    today = today or date.today()
    provider = make_provider(cfg, source, today)
    stats = collect(provider, db, cfg, today)
    print(f"Coleta: {stats['requests']} consultas, {stats['errors']} falhas, {stats['offers']} ofertas guardadas")
    if stats["requests"] and stats["errors"] == stats["requests"]:
        print("Todas as consultas falharam. Confira o token e a conexão (rode: python -m watcher.main selftest).")
        return 2
    deals = find_deals(db, cfg, today)
    fresh = new_alerts(db, deals, cfg, today)
    if fresh and notify:
        send_telegram(format_message(fresh))
        mark_alerted(db, fresh, today)
    elif not fresh:
        print("Nenhuma oferta nova abaixo do esperado.")
    out = render(db, deals, today, provider.name, stats)
    print(f"Painel gerado em {out}")
    return 0


def demo(cfg, db, days=30):
    """Simula `days` dias de histórico com dados fictícios e roda a análise de hoje."""
    today = date.today()
    cfg["search"]["source"] = "mock"
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        collect(MockProvider(d), db, cfg, d)
    return run(cfg, db, source="mock", today=today)


def selftest(cfg):
    token = os.getenv("TRAVELPAYOUTS_TOKEN", "")
    p = TravelpayoutsProvider(token, cfg["search"]["currency"], cfg["search"]["market"])
    today = date.today()
    month = f"{(today + timedelta(days=45)):%Y-%m}"
    data = p.raw("GRU", "LIS", month)
    items = data.get("data") or []
    print(f"success={data.get('success')} · {len(items)} itens para GRU→LIS em {month}")
    if items:
        print("Primeiro item bruto:\n" + json.dumps(items[0], indent=2, ensure_ascii=False))
    offers = p.parse(items, "GRU")
    print(f"{len(offers)} ofertas de ida e volta lidas corretamente")
    return 0 if offers else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="watcher", description="Monitor de passagens")
    ap.add_argument("command", choices=["run", "demo", "selftest", "report"])
    ap.add_argument("--config", default="config.toml")
    ap.add_argument("--db", default="data/prices.db")
    ap.add_argument("--source", choices=["travelpayouts", "mock"])
    ap.add_argument("--no-notify", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = config_mod.load(a.config)
    if a.command == "selftest":
        return selftest(cfg)
    db = DB(":memory:" if a.command == "demo" else a.db)
    if a.command == "demo":
        return demo(cfg, db)
    if a.command == "report":
        today = date.today()
        render(db, find_deals(db, cfg, today), today, cfg["search"]["source"], None)
        print("Painel gerado em site/index.html")
        return 0
    return run(cfg, db, a.source, notify=not a.no_notify)


if __name__ == "__main__":
    sys.exit(main())
