"""
Reconhece itens do jogo e precos dentro de texto livre de mensagens de venda.
Usado por extract_trades.py.
"""
import json
import re
from pathlib import Path
from unidecode import unidecode
from rapidfuzz import fuzz

ITEMS_PATH = Path(__file__).parent.parent / "items_final.json"

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+",
    flags=re.UNICODE,
)

# Mensagens geradas pelo proprio bot do jogo (combate, baus, status, sistema de troca,
# lojas de NPC) nao sao vendas entre jogadores — precisam ser descartadas antes de
# tentar casar item+preco, senao "recompensa de XP" vira "preco de venda".
BOT_NOISE_RE = re.compile(
    r"vit[oó]ria!|derrota\b|ba[uú] encontrado|invent[aá]rio cheio|"
    r"👥\s*online|❤️\s*hp:|⚡\s*energia:|hp:\s*\d+/\d+|"
    r"🤝|confirma[cç][oõ]es:|expira em:|"
    r"loja do \w+|"
    r"subiu de n[ií]vel|level ?up|"
    r"\bxp\b",
    re.IGNORECASE,
)

# gold e tofu sao as moedas "oficiais", mas na pratica os jogadores tambem usam
# chave de masmorra (🔑) e energia (⚡) como forma de pagamento/troca — cada uma
# rastreada separada, nunca misturada numa mesma media/mediana. Os jogadores
# tanto escrevem por extenso ("tofu", "gold", "energia") quanto usam emoji como
# simbolo (🧆 e 🧀 pra tofu — os dois circulam no chat mesmo so 🧆 sendo o icone
# oficial do jogo; 🪙 pra gold; 🔑 pra chave; ⚡ pra energia) ou abreviacoes ("tf").
# "chave"/"chaves" por extenso NAO entra como moeda (ambiguo demais com o proprio
# item "Chave de Masmorra"/"Chave de Ossos" sendo vendido) — so o emoji 🔑, que e
# inequivoco.
GOLD_WORDS = {"gold", "ouro", "moeda", "moedas", "coin", "coins", "g", "od"}
TOFU_WORDS = {"tofu", "tofus", "tf", "tufo", "tufos"}
ENERGY_WORDS = {"energia", "energias"}
STARDUST_WORDS = {"poeira", "poeiras"}
# "poeira"/"poeiras" so conta como moeda quando NAO vier seguido de "estelar" —
# nesse caso e o nome do item Poeira Estelar sendo vendido/descrito (quantidade,
# nao pagamento), ex "vendo 5 poeira estelar por 10 tofu" (5 = quantidade do item).
CURRENCY_PATTERN = (
    r"(gold|ouro|tofus?|tufos?|moedas?|coins?|energias?|poeiras?(?!\s+estelar)|"
    r"\btf\b|\bg\b|\bod\b|🪙|💰|🧆|🧀|🔑|🗝️?|⚡)"
)
# conector opcional entre o "k" (mil) e a moeda: "15k de ouro", "20k gold",
# "70k( apenas gold)" — aceita espacos, parenteses e as palavras de ligacao
# em qualquer combinacao entre o numero e a moeda.
CONNECTOR = r"[\s()]*(?:(?:de|apenas|s[oó])[\s()]*)*"

PRICE_RE = re.compile(
    r"(\d+(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(k\b)?" + CONNECTOR + CURRENCY_PATTERN,
    re.IGNORECASE,
)
PRICE_RE_REVERSED = re.compile(
    CURRENCY_PATTERN + CONNECTOR + r"[:\-]?\s*(\d+(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(k\b)?",
    re.IGNORECASE,
)

# palavras de venda/compra e moeda/numero atrapalham o token_set_ratio (diluem
# a comparacao com muita gente estranha ao redor do nome do item de verdade).
NOISE_WORDS_RE = re.compile(
    r"\b(vendo|compro|venda|compra|troco|troca|cada|apenas|somente|barato|ou|"
    r"promocao|por|pago|preco|gold|ouro|tofus?|tufos?|moedas?|coins?|energias?|g|od|k|tf)\b"
)


def strip_noise_words(norm_text):
    t = NOISE_WORDS_RE.sub(" ", norm_text)
    t = re.sub(r"\d+k?\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normalize(text):
    text = EMOJI_RE.sub(" ", text)
    text = unidecode(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_bot_noise(text):
    return bool(BOT_NOISE_RE.search(text))


def load_items():
    items = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    indexed = []
    for it in items:
        norm = normalize(it["name"])
        if len(norm) < 3:
            continue
        indexed.append({"key": it["key"], "name": it["name"], "norm": norm})
    # match longer names first so "Anel de Prata" wins over generic "Anel"
    indexed.sort(key=lambda x: -len(x["norm"]))
    return indexed


ITEMS = load_items()
ITEMS_BY_KEY = {i["key"]: i for i in ITEMS}

# apelidos que os jogadores usam e que NAO batem por fuzzy (palavras totalmente
# diferentes do nome oficial, nao erro de digitacao/abreviacao) — mapeamento
# manual, curado a partir de casos vistos no chat.
MANUAL_ALIASES = {
    "botas do sol": "boots_solar_step",
}
MANUAL_ALIASES_NORM = {normalize(alias): key for alias, key in MANUAL_ALIASES.items()}


def currency_of(word):
    if word in ("🪙", "💰"):
        return "gold"
    if word in ("🧆", "🧀"):
        return "tofu"
    if word in ("🔑", "🗝️", "🗝"):
        return "chave"
    if word == "⚡":
        return "energia"
    w = unidecode(word).lower()
    if w in GOLD_WORDS:
        return "gold"
    if w in TOFU_WORDS:
        return "tofu"
    if w in ENERGY_WORDS:
        return "energia"
    if w in STARDUST_WORDS:
        return "poeira"
    return None


def parse_price_number(raw, has_k):
    cleaned = re.sub(r"[.,](?=\d{3}(\D|$))", "", raw)
    cleaned = cleaned.replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if has_k:
        value *= 1000
    return value


def find_prices(original_text):
    """Retorna lista de {"value": float, "currency": "gold"|"tofu"}, sem duplicatas."""
    found = []
    for m in PRICE_RE.finditer(original_text):
        val = parse_price_number(m.group(1), bool(m.group(2)))
        cur = currency_of(m.group(3))
        if val and cur:
            found.append({"value": val, "currency": cur})
    for m in PRICE_RE_REVERSED.finditer(original_text):
        val = parse_price_number(m.group(2), bool(m.group(3)))
        cur = currency_of(m.group(1))
        if val and cur:
            found.append({"value": val, "currency": cur})

    seen = set()
    unique = []
    for p in found:
        key = (p["value"], p["currency"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def find_items(norm_text, window_threshold=90, token_threshold=85):
    matched = []
    remaining = norm_text
    for alias_norm, key in MANUAL_ALIASES_NORM.items():
        if alias_norm in remaining:
            matched.append((ITEMS_BY_KEY[key], 100))
            remaining = remaining.replace(alias_norm, " ")
    for item in ITEMS:
        if item["norm"] in remaining:
            matched.append((item, 100))
            remaining = remaining.replace(item["norm"], " ")
    if not matched:
        # dois metodos fuzzy, cada um cobre um tipo de variacao que o match exato
        # (substring) nao pega:
        #  - janela de palavras do MESMO tamanho do nome do item: pega erro de
        #    digitacao/plural/acento (ex "chave de osso" vs "Chave de Ossos").
        #  - token_set_ratio contra a linha SEM as palavras de venda/moeda/numero:
        #    pega nome ABREVIADO, faltando palavra(s) do meio ou do fim (ex
        #    "Martelo do Gibby" vs "Martelo Magico do Gibby"), sem se importar
        #    com ordem/palavras extras. Sem a limpeza de ruido o placar fica
        #    diluido demais por "vendo... por... gold" e nunca bate o threshold.
        # nenhum dos dois deve casar so por uma palavra solta em comum — por isso
        # os thresholds altos (validado contra falsos positivos conhecidos).
        words = norm_text.split()
        cleaned = strip_noise_words(norm_text)
        best = None
        best_score = 0
        for item in ITEMS:
            item_len = len(item["norm"].split())
            for span in {max(1, item_len - 1), item_len, item_len + 1}:
                if span > len(words):
                    continue
                for start in range(0, len(words) - span + 1):
                    window = " ".join(words[start:start + span])
                    score = fuzz.ratio(item["norm"], window)
                    if score > best_score:
                        best_score, best = score, item

            if cleaned:
                token_score = fuzz.token_set_ratio(item["norm"], cleaned)
                if token_score >= token_threshold and token_score > best_score:
                    best_score, best = token_score, item

        if best and best_score >= min(window_threshold, token_threshold):
            matched.append((best, best_score))
    return matched


def _line_result(line):
    norm = normalize(line)
    items = find_items(norm)
    prices = find_prices(line)
    # preco "confiavel" e 1 item + 1 preco (caso simples), OU 1 item + varios
    # precos em MOEDAS DIFERENTES (comum: "Item — 5 tofu | 25k gold", o mesmo
    # item anunciado por mais de uma forma de pagamento vira uma venda por moeda).
    # dois precos na MESMA moeda e ambiguo (poderia ser range, estoque, outro
    # item citado) — isso continua indo pra revisao.
    currencies = [p["currency"] for p in prices]
    confident = len(items) == 1 and prices and len(currencies) == len(set(currencies))
    return {
        "items": [{"key": i["key"], "name": i["name"], "score": s} for i, s in items],
        "prices": prices,
        "confident": confident,
    }


def analyze_message(text):
    """
    Retorna None se a mensagem inteira for ruido de bot/sistema.
    Caso contrario, retorna:
      {
        "trades": [ {item, price, currency, line}, ... ],   # pares confiaveis (1 item + 1 preco por linha)
        "leftover": [ {items, prices, text}, ... ],          # linhas ambiguas, pra revisao manual
      }
    Mensagens com varios itens listados um por linha (comum em "VENDO: item - preco")
    sao processadas linha a linha; mensagens de uma linha so caem no caso simples.
    """
    if is_bot_noise(text):
        return None

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    def trades_from(result, line):
        return [
            {
                "item_key": result["items"][0]["key"],
                "item_name": result["items"][0]["name"],
                "price": p["value"],
                "currency": p["currency"],
                "line": line,
            }
            for p in result["prices"]
        ]

    trades = []
    leftover = []

    if len(lines) == 1:
        result = _line_result(lines[0])
        if result["confident"]:
            trades.extend(trades_from(result, lines[0]))
        elif result["items"] or result["prices"]:
            leftover.append({"items": result["items"], "prices": result["prices"], "text": lines[0]})
        return {"trades": trades, "leftover": leftover}

    # mensagem multi-linha: tenta casar item+preco por linha; se uma linha nao
    # tiver preco proprio mas a proxima linha tiver so preco (formato "item \n preco"),
    # junta as duas.
    i = 0
    while i < len(lines):
        result = _line_result(lines[i])
        if result["confident"]:
            trades.extend(trades_from(result, lines[i]))
            i += 1
            continue

        if result["items"] and not result["prices"] and i + 1 < len(lines):
            next_result = _line_result(lines[i + 1])
            next_currencies = [p["currency"] for p in next_result["prices"]]
            if (next_result["prices"] and not next_result["items"] and len(result["items"]) == 1
                    and len(next_currencies) == len(set(next_currencies))):
                combined = {"items": result["items"], "prices": next_result["prices"]}
                trades.extend(trades_from(combined, lines[i] + " / " + lines[i + 1]))
                i += 2
                continue

        if result["items"] or result["prices"]:
            leftover.append({"items": result["items"], "prices": result["prices"], "text": lines[i]})
        i += 1

    return {"trades": trades, "leftover": leftover}
