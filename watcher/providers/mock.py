"""Dados FICTÍCIOS, só para testar o fluxo (coleta → análise → alertas → painel)."""
import calendar
import math
import random
from datetime import date, timedelta

from ..models import Offer

BASE = {"SSA": 1000, "REC": 1100, "FOR": 1100, "NAT": 1100, "MCZ": 1100, "FLN": 750,
        "LIS": 4200, "SCL": 1700, "EZE": 1400, "MVD": 1500, "MIA": 3900, "MAD": 4000,
        "NYC": 4300, "PAR": 4400, "LON": 4500, "CUN": 4300, "BOG": 2600, "LIM": 2300}
ORIGIN_FACTOR = {"GRU": 1.0, "CGH": 1.05, "VCP": 0.86}


class MockProvider:
    name = "mock"

    def __init__(self, as_of: date | None = None):
        self.as_of = as_of or date.today()

    def search_month(self, origin, destination, month):
        y, m = map(int, month.split("-"))
        dests = [destination] if destination else list(BASE)
        out = []
        for dest in dests:
            base = BASE.get(dest, 2500) * ORIGIN_FACTOR.get(origin, 1.0)
            for day in range(1, calendar.monthrange(y, m)[1] + 1):
                for length in (5, 7, 10, 14):
                    dep = date(y, m, day)
                    ret = dep + timedelta(days=length)
                    lead = (dep - self.as_of).days
                    if lead < 0:
                        continue
                    r = random.Random(f"{origin}{dest}{dep}{ret}{self.as_of}")
                    season = 1 + 0.2 * math.sin((dep.month - 1) / 12 * 2 * math.pi)
                    urgency = 1 + 0.5 * max(0, (30 - lead) / 30)
                    price = base * season * urgency * (0.9 + 0.3 * r.random())
                    if r.random() < 0.03:
                        price *= 0.6          # promoção fictícia
                    out.append(Offer(origin, dest, dest, dep, ret, round(price), r.choice([0, 1, 1]),
                                     "XX", f"https://example.com/{origin}-{dest}-{dep}", "mock"))
        return out
