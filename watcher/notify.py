import os
from urllib.parse import quote

import requests

from .airports import name
from .models import Deal


def brl(v: float) -> str:
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def gflights_link(o) -> str:
    q = f"Flights from {o.origin} to {o.dest_airport or o.dest} on {o.depart} through {o.ret}"
    return "https://www.google.com/travel/flights?q=" + quote(q)


def format_deal(d: Deal) -> str:
    o = d.offer
    esc = "direto" if o.transfers == 0 else (f"{o.transfers} escala" if o.transfers == 1 else "")
    when = f"{o.depart:%d/%m} → {o.ret:%d/%m/%Y} ({o.trip_days} dias)"
    lines = [f"✈️ {name(o.origin)} → {name(o.dest)}",
             f"{brl(o.price)} · {when}" + (f" · {esc}" if esc else ""),
             "• " + "; ".join(d.reasons),
             f"Confirmar: {gflights_link(o)}"]
    return "\n".join(lines)


def format_message(deals: list[Deal]) -> str:
    head = f"🔔 {len(deals)} oferta(s) abaixo do esperado (preços em cache, confirme antes de comprar)\n"
    return head + "\n\n".join(format_deal(d) for d in deals)


def send_telegram(text: str) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[Telegram não configurado — mensagem abaixo]\n" + text)
        return False
    for i in range(0, len(text), 3900):  # limite do Telegram: 4096
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text[i:i + 3900],
                                "disable_web_page_preview": "true"}, timeout=20)
        r.raise_for_status()
    return True
