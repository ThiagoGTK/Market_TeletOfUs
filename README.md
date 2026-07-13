# Codex de Equipamentos — Teletofus RPG

Companion não-oficial do [Teletofus RPG](https://teletofus.com) (o RPG do Telegram). Mostra, por classe e nível, todos os itens que dá pra conseguir — onde farmar, atributos, chance de drop — e o **preço de mercado real**, calculado a partir dos anúncios de compra/venda no grupo do jogo no Telegram.

Não é afiliado à equipe do Teletofus.

## O que tem aqui

- **`codex.html`** / **`index.html`** — a página em si (os dois são idênticos; `index.html` existe só pra servir via GitHub Pages). Arquivo único (HTML + CSS + dados embutidos), sem dependências externas — abre em qualquer navegador.
- **Catálogo de itens** (`items_final.json`, `bonus_items.json`, `build_data.js`) — 218 itens (armas, armaduras, acessórios, consumíveis, chaves, skins e habilidades especiais de boss), com classe, nível, mapa de drop e raridade.
- **`telegram_market/`** — pipeline em Python que lê o tópico de vendas do grupo do Telegram, reconhece item + preço em texto livre e calcula o preço mediano de mercado.

## Como funciona o catálogo de itens

Os dados de itens vêm do próprio bundle JavaScript público do site oficial (`teletofus.com`), que carrega o banco de itens do jogo direto no código da página. `build_data.js` processa esse banco e gera `items_final.json`, mesclando também:

- **`bonus_items.json`** — itens especiais/habilidades de boss ("Almas") e recompensas de skin que não aparecem na wiki pública do site, cadastrados manualmente a partir de dados encontrados no próprio jogo.
- **`telegram_market/market_prices.json`** — os preços de mercado calculados (veja abaixo).

Pra regenerar `items_final.json` depois de mudar `bonus_items.json` ou atualizar os preços:

```bash
node build_data.js
```

E pra embutir o resultado dentro do `codex.html`:

```bash
node -e "const fs=require('fs'); fs.writeFileSync('items.js.txt','const ITEMS = '+JSON.stringify(require('./items_final.json'))+';');"
node inject_items.js
cp codex.html index.html   # index.html precisa ficar igual, e' o que o GitHub Pages serve
```

## Como funciona o preço de mercado

O jogo roda dentro de um grupo do Telegram, com um tópico "Vendas e Trocas" onde jogadores anunciam preços em texto livre (sem formato fixo). O pipeline em `telegram_market/` faz:

1. **`fetch_history.py`** — usa sua própria conta do Telegram (via [Telethon](https://docs.telethon.dev)) pra baixar o histórico de mensagens do tópico de vendas.
2. **`monitor_live.py`** — alternativa pra acompanhar mensagens novas em tempo real.
3. **`extract_trades.py`** — reconhece item + preço em cada mensagem (`matching.py`), usando:
   - correspondência exata e aproximada (fuzzy) de nomes de item contra o catálogo, tolerando abreviações, plural/singular e erros de digitação;
   - reconhecimento de **5 moedas diferentes**: gold 🪙, tofu 🧀, chave de masmorra 🔑, energia ⚡ e poeira estelar ✨ (por extenso, emoji ou abreviação);
   - descarte de mensagens automáticas do bot do jogo (combate, baú, status, sistema de troca) que não são vendas reais.
4. **`compute_prices.py`** — agrega os anúncios reconhecidos em mediana/média/mín/máx por item e por moeda, gerando `market_prices.json`.

Mensagens ambíguas (0 ou 2+ itens, ou sem preço reconhecido) vão para `review_needed.csv`, pra revisão manual.

### Configurar

```bash
cd telegram_market
pip install -r requirements.txt
cp config.example.py config.py
```

Edite `config.py` com:
- `API_ID` / `API_HASH` — gerados em [my.telegram.org/apps](https://my.telegram.org/apps) (login com seu número, qualquer nome de app serve)
- `PHONE` — seu número, formato internacional
- `CHAT` / `TOPIC_ID` — identificador do grupo e do tópico de vendas (rode `list_chats.py` e `list_topics.py` pra descobrir)

**`config.py` e a sessão do Telegram (`*.session`) nunca devem ser commitados** — já estão no `.gitignore`. São credenciais da sua conta pessoal.

### Rodar

```bash
python fetch_history.py       # historico completo (uma vez)
python extract_trades.py      # reconhece item+preco
python compute_prices.py      # calcula mediana/faixa por item e moeda
```

Pra atualizar os preços mais pra frente, rode os três de novo — `fetch_history.py` só baixa mensagens novas, não duplica.

## Limitações conhecidas

- Preços vêm de **anúncios**, não de vendas confirmadas — não há como saber se a negociação realmente aconteceu naquele valor.
- Alguns itens especiais (drops únicos de boss) não têm nível/local documentado oficialmente; ficam marcados como "Desconhecido".
- Reconhecimento de texto livre é heurístico — sempre vai haver uma fatia de mensagens que caem em `review_needed.csv` por ambiguidade genuína (múltiplos itens numa mensagem, gíria não mapeada, etc).
