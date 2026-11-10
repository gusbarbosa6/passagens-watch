"""Fonte de preços: Travelpayouts / Aviasales Data API (gratuita, com token).

ATENÇÃO: são preços em *cache* (de buscas recentes de usuários da Aviasales), não
preços ao vivo. Sempre confirme no site da companhia / Google Flights antes de comprar.
Docs: https://support.travelpayouts.com/hc/en-us/articles/203956163
"""
import time
from datetime import date

import requests

from ..models import Offer

URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
SITE = "https://www.aviasales.com"


class TravelpayoutsError(RuntimeError):
    pass


class TravelpayoutsProvider:
    name = "travelpayouts"

    def __init__(self, token: str, currency="brl", market="br", sleep=0.4, retries=3):
        if not token:
            raise TravelpayoutsError("Defina a variável de ambiente TRAVELPAYOUTS_TOKEN.")
        self.token, self.currency, self.market = token, currency, market
        self.sleep, self.retries = sleep, retries
        self.session = requests.Session()
        self.session.headers.update({"X-Access-Token": token, "Accept-Encoding": "gzip, deflate"})

    def _get(self, params: dict) -> dict:
        last = None
        for attempt in range(self.retries):
            try:
                r = self.session.get(URL, params=params, timeout=30)
                if r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                r.raise_for_status()
                data = r.json()
                if not data.get("success", True):
                    raise TravelpayoutsError(f"API devolveu erro: {data.get('error')}")
                time.sleep(self.sleep)
                return data
            except (requests.RequestException, ValueError) as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise TravelpayoutsError(f"falha após {self.retries} tentativas: {last}")

    def raw(self, origin: str, destination: str | None, month: str) -> dict:
        return self._get(self._params(origin, destination, month))

    def _params(self, origin, destination, month):
        p = {
            "origin": origin, "departure_at": month, "one_way": "false",
            "currency": self.currency, "market": self.market, "limit": 1000,
            "sorting": "price",
        }
        if destination:
            p["destination"] = destination
        else:  # qualquer destino: um resultado (o mais barato) por destino
            p["unique"] = "true"
        return p

    def search_month(self, origin, destination, month) -> list[Offer]:
        data = self.raw(origin, destination, month)
        return self.parse(data.get("data") or [], origin)

    @staticmethod
    def parse(items: list, origin: str) -> list[Offer]:
        out = []
        for it in items:
            try:
                dep = date.fromisoformat(str(it["departure_at"])[:10])
                ret_raw = it.get("return_at")
                if not ret_raw:
                    continue  # só ida e volta
                ret = date.fromisoformat(str(ret_raw)[:10])
                link = it.get("link") or ""
                if link.startswith("/"):
                    link = SITE + link
                out.append(Offer(
                    origin=origin,
                    dest=str(it.get("destination") or it.get("destination_airport")),
                    dest_airport=str(it.get("destination_airport") or it.get("destination") or ""),
                    depart=dep, ret=ret, price=float(it["price"]),
                    transfers=it.get("transfers"), airline=str(it.get("airline") or ""),
                    link=link, source="travelpayouts",
                ))
            except (KeyError, ValueError, TypeError):
                continue  # item fora do formato esperado: ignora
        return out
