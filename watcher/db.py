import os
import sqlite3
from datetime import date, timedelta

from .models import Offer

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers(
  day TEXT NOT NULL, origin TEXT NOT NULL, dest TEXT NOT NULL, dest_airport TEXT,
  depart TEXT NOT NULL, ret TEXT NOT NULL, lead INTEGER NOT NULL,
  price REAL NOT NULL, transfers INTEGER, airline TEXT, link TEXT, source TEXT,
  PRIMARY KEY(day, origin, dest, depart, ret)
);
CREATE INDEX IF NOT EXISTS ix_route ON offers(origin, dest, day);
CREATE TABLE IF NOT EXISTS alerts(key TEXT PRIMARY KEY, price REAL, alerted_at TEXT);
"""


class DB:
    def __init__(self, path="data/prices.db"):
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SCHEMA)

    def upsert_offers(self, day: date, offers: list[Offer]):
        self.c.executemany(
            """INSERT INTO offers(day,origin,dest,dest_airport,depart,ret,lead,price,transfers,airline,link,source)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(day,origin,dest,depart,ret) DO UPDATE SET
                 price=excluded.price, transfers=excluded.transfers, airline=excluded.airline,
                 link=excluded.link WHERE excluded.price < offers.price""",
            [(day.isoformat(), o.origin, o.dest, o.dest_airport, o.depart.isoformat(), o.ret.isoformat(),
              (o.depart - day).days, o.price, o.transfers, o.airline, o.link, o.source) for o in offers])
        self.c.commit()

    def prune(self, today: date, keep_days: int):
        self.c.execute("DELETE FROM offers WHERE day < ?", ((today - timedelta(days=keep_days)).isoformat(),))
        self.c.commit()

    def offers_for_day(self, day: date) -> list[sqlite3.Row]:
        return self.c.execute("SELECT * FROM offers WHERE day=?", (day.isoformat(),)).fetchall()

    def history(self, origin, dest, lead_lo, lead_hi, since: date, before: date):
        rows = self.c.execute(
            """SELECT price, day FROM offers WHERE origin=? AND dest=? AND lead>=? AND lead<?
               AND day>=? AND day<?""",
            (origin, dest, lead_lo, lead_hi, since.isoformat(), before.isoformat())).fetchall()
        return [r["price"] for r in rows], len({r["day"] for r in rows})

    def daily_min(self, dest, since: date):
        return self.c.execute(
            "SELECT day, MIN(price) p FROM offers WHERE dest=? AND day>=? GROUP BY day ORDER BY day",
            (dest, since.isoformat())).fetchall()

    def get_alert(self, key):
        return self.c.execute("SELECT * FROM alerts WHERE key=?", (key,)).fetchone()

    def put_alert(self, key, price, when: date):
        self.c.execute("INSERT OR REPLACE INTO alerts VALUES(?,?,?)", (key, price, when.isoformat()))
        self.c.commit()
