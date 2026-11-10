# Monitor de passagens ✈️

Varre preços de voos (ida e volta) saindo de **GRU, CGH** (e **VCP** só se for bem mais barato),
sem data fixa: olha os próximos meses, guarda o histórico e te **avisa no Telegram** quando
aparece algo **abaixo da sua meta** ou **abaixo do que costuma custar**. Também gera um painel
com "quanto custa sair logo" (próximos 14/30/60/90 dias) — bom para estimar férias de última hora.

Custo: **R$ 0** (API gratuita + GitHub Actions + Telegram).

> ⚠️ Os preços vêm de **cache** da Travelpayouts/Aviasales (buscas recentes de outros usuários),
> não são ao vivo. Use como radar e **confirme no Google Flights** (o alerta já traz o link).
> Só voos; hospedagem não está incluída.

## Como funciona

```
GitHub Actions (1x/dia) → Coleta → SQLite (histórico) → Análise → Telegram + painel HTML
```

* **Coleta:** para cada origem × mês × destino da sua lista (+ "qualquer destino"), pede as
  ofertas mais baratas e filtra por duração da viagem (5–15 dias), escalas e antecedência.
* **"Abaixo do esperado"** (qualquer um dos critérios):
  1. preço ≤ sua **meta** para o destino;
  2. preço entre os 20% mais baixos **e** ≥15% abaixo da mediana do histórico (separado por
     faixa de antecedência: 0–30, 30–60, 60–120, 120+ dias);
  3. enquanto o histórico é curto (primeiras ~semanas): ≥25% abaixo da mediana da varredura de hoje.
* **VCP:** só entra se for pelo menos 15% mais barato que o melhor preço de GRU/CGH para o mesmo destino.
* **Sem spam:** o mesmo alerta só se repete depois de 7 dias, ou se o preço cair mais de 5%.

## Passo a passo

### 1) Token da API de preços (grátis)
1. Crie conta em <https://www.travelpayouts.com> e copie seu **API token** (Perfil → API token).
2. Teste a chamada real (importante, veja a nota abaixo):
   ```bash
   pip install -r requirements.txt
   export TRAVELPAYOUTS_TOKEN=seu_token
   python -m watcher.main selftest
   ```
   Deve mostrar "N ofertas de ida e volta lidas corretamente". Se vier 0 ou erro, me mande a saída.

### 2) Bot do Telegram (grátis)
1. No Telegram, fale com **@BotFather** → `/newbot` → guarde o **token**.
2. Mande qualquer mensagem para o seu bot e abra
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → procure `"chat":{"id": 123456789`. Esse é o **chat id**.

### 3a) Rodar sozinho todo dia, no GitHub (recomendado)
1. Crie um repositório e suba esta pasta. Dica: repositório **público** tem Actions ilimitado e
   permite o Pages; os tokens ficam nos *Secrets*, não no código.
2. Settings → Secrets and variables → Actions → adicione `TRAVELPAYOUTS_TOKEN`,
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Aba **Actions** → "monitor-passagens" → **Run workflow** para testar. Depois roda todo dia às 06:17.
4. O painel fica em *Artifacts → painel* de cada execução (baixe e abra `index.html`).

### 3b) Ou rodar no seu computador
```bash
python -m watcher.main run        # coleta + análise + alerta + painel (site/index.html)
```
Agende com `cron` (Mac/Linux) ou Agendador de Tarefas (Windows).

### Testar sem API
```bash
python -m watcher.main demo       # dados FICTÍCIOS, 30 dias de histórico simulado
python -m unittest discover -s tests
```

## Ajustes (config.toml)
* **destinos e metas:** seção `[destinations.watch]` (os valores atuais são chutes — ajuste!).
* **janela de busca, duração da viagem, escalas:** seção `[search]`.
* **sensibilidade dos alertas:** seção `[alerts]`.
* **"qualquer destino":** `anywhere = true`; para alertar destinos fora da lista, defina
  `discovery_max_price` (ex.: 1500).

## Limites e pontos de atenção
* A chamada real à API **não foi testada** pelo autor (ambiente sem acesso à internet livre) — por isso o
  comando `selftest`. Os campos de resposta seguem a documentação da Travelpayouts.
* Cache de preços: pode haver ofertas que já não existem.
* Se um dia a Travelpayouts mudar/limitar o acesso gratuito, basta criar outro provedor em
  `watcher/providers/` (uma função `search_month`) — o resto do sistema não muda.
