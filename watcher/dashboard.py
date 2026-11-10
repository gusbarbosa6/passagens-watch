import html
from datetime import date, datetime, timedelta
from pathlib import Path

from .airports import name
from .analyze import window_summary
from .db import DB
from .models import Deal
from .notify import brl, gflights_link

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--fg:#1b1f24;--mut:#5f6b7a;--line:#e3e7ec;--acc:#0b6bcb;--good:#0a7d3b}
@media (prefers-color-scheme:dark){:root{--bg:#12151a;--card:#1a1f26;--fg:#e8ecf1;--mut:#97a3b3;--line:#2a313b;--acc:#5aa8ff;--good:#4cc97f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:1000px;margin:0 auto;padding:20px 16px 48px}h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;margin:28px 0 10px}.sub{color:var(--mut);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.warn{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:8px;padding:10px 12px;margin:14px 0;color:var(--mut);font-size:13px}
table{width:100%;border-collapse:collapse}th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.03em}
tr:last-child td{border-bottom:0}.price{font-weight:700;white-space:nowrap}.good{color:var(--good)}
.mut{color:var(--mut);font-size:13px}a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.scroll{overflow-x:auto}.spark{display:inline-block;vertical-align:middle}
@media(max-width:640px){th,td{padding:8px}}
"""


def sparkline(values, w=110, h=28):
    if len(values) < 2:
        return '<span class="mut">—</span>'
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pts = " ".join(f"{i / (len(values) - 1) * w:.1f},{h - 3 - (v - lo) / span * (h - 6):.1f}"
                   for i, v in enumerate(values))
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="evolução do menor preço"><polyline fill="none" stroke="currentColor" '
            f'stroke-width="1.6" points="{pts}"/></svg>')


def render(db: DB, deals: list[Deal], today: date, source: str, stats: dict | None, out="site/index.html"):
    e = html.escape
    rows = []
    for d in deals[:40]:
        o = d.offer
        esc = "direto" if o.transfers == 0 else (f"{o.transfers} escala" if o.transfers == 1 else "—")
        links = f'<a href="{e(gflights_link(o))}" target="_blank" rel="noopener">Google Flights</a>'
        if o.link.startswith("http"):
            links += f' · <a href="{e(o.link)}" target="_blank" rel="noopener">fonte</a>'
        rows.append(
            f"<tr><td><b>{e(name(o.dest))}</b><div class='mut'>de {e(name(o.origin))}</div></td>"
            f"<td>{o.depart:%d/%m} → {o.ret:%d/%m/%Y}<div class='mut'>{o.trip_days} dias · {esc}</div></td>"
            f"<td class='price good'>{brl(o.price)}</td>"
            f"<td class='mut'>{e('; '.join(d.reasons))}</td><td>{links}</td></tr>")
    deals_html = ("".join(rows) if rows else
                  "<tr><td colspan='5' class='mut'>Nada abaixo do esperado nesta varredura.</td></tr>")

    summary = window_summary(db, today)
    srows = []
    since = today - timedelta(days=60)
    for r in summary[:30]:
        cells = ""
        for w in (14, 30, 60, 90):
            x = r["windows"].get(w)
            if x:
                b = x["best"]
                cells += (f"<td class='price'>{brl(b.price)}<div class='mut'>{b.depart:%d/%m} · "
                          f"mediana {brl(x['median'])}</div></td>")
            else:
                cells += "<td class='mut'>—</td>"
        spark = sparkline([row["p"] for row in db.daily_min(r["dest"], since)])
        srows.append(f"<tr><td><b>{e(name(r['dest']))}</b></td>{cells}<td>{spark}</td></tr>")

    st = ""
    if stats:
        st = f" · {stats['requests']} consultas, {stats['errors']} falhas"
    banner = ""
    if source == "mock":
        banner = ('<div class="warn"><b>DADOS FICTÍCIOS</b> — gerados pelo modo de teste. '
                  'Nada aqui é preço real.</div>')
    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Monitor de Passagens</title>
<style>{CSS}</style></head><body><main>
<h1>Monitor de passagens</h1>
<div class="sub">Atualizado em {datetime.now():%d/%m/%Y %H:%M} · fonte: {e(source)}{e(st)}</div>
{banner}
<div class="warn">Preços vêm de cache (buscas recentes de outros usuários) e podem estar desatualizados.
Confirme no Google Flights ou no site da companhia antes de comprar. Só voos (sem hospedagem).</div>
<h2>Abaixo do esperado</h2>
<div class="card scroll"><table><thead><tr><th>Destino</th><th>Datas</th><th>Preço (ida e volta)</th>
<th>Por quê</th><th>Conferir</th></tr></thead><tbody>{deals_html}</tbody></table></div>
<h2>Quanto custa sair logo?</h2>
<div class="sub" style="margin-bottom:8px">Menor preço encontrado para saídas dentro de cada janela, com a mediana
das ofertas coletadas. Útil para estimar férias de última hora.</div>
<div class="card scroll"><table><thead><tr><th>Destino</th><th>Até 14 dias</th><th>Até 30 dias</th>
<th>Até 60 dias</th><th>Até 90 dias</th><th>Menor preço / dia (60d)</th></tr></thead>
<tbody>{"".join(srows)}</tbody></table></div>
</main></body></html>"""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(page, encoding="utf-8")
    return out
