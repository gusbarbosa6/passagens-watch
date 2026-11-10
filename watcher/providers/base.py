from typing import Protocol

from ..models import Offer


class Provider(Protocol):
    name: str

    def search_month(self, origin: str, destination: str | None, month: str) -> list[Offer]:
        """Ofertas de ida e volta saindo de `origin` no mês `month` (YYYY-MM).
        `destination=None` significa "qualquer destino"."""
        ...
