from dataclasses import dataclass
from datetime import date


@dataclass
class Offer:
    origin: str
    dest: str            # código do destino (cidade ou aeroporto) como a fonte devolve
    dest_airport: str    # aeroporto de destino, se a fonte informar
    depart: date
    ret: date
    price: float
    transfers: int | None
    airline: str
    link: str
    source: str

    @property
    def trip_days(self) -> int:
        return (self.ret - self.depart).days


@dataclass
class Deal:
    offer: Offer
    reasons: list
    ref_price: float | None   # preço de referência (mediana) usado na comparação
    discount: float           # 0.25 = 25% abaixo da referência
    kind: str                 # "meta", "historico", "varredura", "descoberta"
