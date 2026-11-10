import unittest
from datetime import date, timedelta

from watcher import config as config_mod
from watcher.analyze import find_deals, new_alerts, mark_alerted
from watcher.collect import _keep, months_to_scan
from watcher.db import DB
from watcher.models import Offer
from watcher.providers.travelpayouts import TravelpayoutsProvider

TODAY = date(2026, 11, 9)


def offer(price, origin="GRU", dest="LIS", dep_in=40, length=8, transfers=1):
    dep = TODAY + timedelta(days=dep_in)
    return Offer(origin, dest, dest, dep, dep + timedelta(days=length), price, transfers, "TP", "", "t")


def cfg():
    c = config_mod.load("nao-existe.toml")
    c["destinations"]["watch"] = {"LIS": 3000}
    c["origins"] = {"primary": ["GRU", "CGH"], "secondary": {"VCP": 0.15}}
    return c


class Tests(unittest.TestCase):
    def test_months(self):
        self.assertEqual(months_to_scan(date(2026, 11, 9), 3), ["2026-11", "2026-12", "2027-01"])

    def test_filters(self):
        c = cfg()
        offers = [offer(1000, length=2), offer(1000, length=30), offer(1000, transfers=3),
                  offer(1000, dep_in=1), offer(1000)]
        self.assertEqual(len(_keep(offers, c, TODAY)), 1)

    def test_target_alert_and_dedupe(self):
        db, c = DB(":memory:"), cfg()
        db.upsert_offers(TODAY, [offer(2900)])
        deals = find_deals(db, c, TODAY)
        self.assertEqual(len(deals), 1)
        self.assertIn("meta", deals[0].reasons[0])
        fresh = new_alerts(db, deals, c, TODAY)
        self.assertEqual(len(fresh), 1)
        mark_alerted(db, fresh, TODAY)
        self.assertEqual(new_alerts(db, find_deals(db, c, TODAY), c, TODAY + timedelta(days=1)), [])
        # queda >5% volta a alertar
        db.upsert_offers(TODAY + timedelta(days=1), [offer(2500)])
        again = new_alerts(db, find_deals(db, c, TODAY + timedelta(days=1)), c, TODAY + timedelta(days=1))
        self.assertEqual(len(again), 1)

    def test_no_deal_above_target(self):
        db, c = DB(":memory:"), cfg()
        db.upsert_offers(TODAY, [offer(3500)])
        self.assertEqual(find_deals(db, c, TODAY), [])

    def test_history_deal(self):
        db, c = DB(":memory:"), cfg()
        c["destinations"]["watch"] = {}
        for i in range(1, 11):  # 10 dias de histórico, ~4 ofertas por dia, em torno de 4000
            d = TODAY - timedelta(days=i)
            db.upsert_offers(d, [Offer("GRU", "LIS", "LIS", d + timedelta(days=40 + k), d + timedelta(days=48 + k),
                                       4000 + 50 * k, 1, "", "", "t") for k in range(5)])
        db.upsert_offers(TODAY, [offer(2900)])
        deals = find_deals(db, c, TODAY)
        self.assertEqual(len(deals), 1)
        self.assertEqual(deals[0].kind, "historico")

    def test_secondary_origin_rule(self):
        db, c = DB(":memory:"), cfg()
        c["destinations"]["watch"] = {"LIS": 9999}
        db.upsert_offers(TODAY, [offer(4000, "GRU"), offer(3700, "VCP", dep_in=41),   # só 7,5% mais barato
                                 offer(3300, "VCP", dep_in=42)])                       # 17,5% mais barato
        origins = {d.offer.origin for d in find_deals(db, c, TODAY)}
        self.assertIn("VCP", origins)
        deals_vcp = [d for d in find_deals(db, c, TODAY) if d.offer.origin == "VCP"]
        self.assertEqual(deals_vcp[0].offer.price, 3300)

    def test_parse_provider(self):
        items = [{"destination": "LIS", "destination_airport": "LIS", "price": 3100,
                  "departure_at": "2026-12-20T10:00:00-03:00", "return_at": "2026-12-30T08:00:00+00:00",
                  "transfers": 0, "airline": "TP", "link": "/search/x"},
                 {"destination": "MAD", "price": 100, "departure_at": "2026-12-20T10:00:00-03:00"},  # só ida
                 {"quebrado": True}]
        out = TravelpayoutsProvider.parse(items, "GRU")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].trip_days, 10)
        self.assertTrue(out[0].link.startswith("https://www.aviasales.com/search"))


if __name__ == "__main__":
    unittest.main()
