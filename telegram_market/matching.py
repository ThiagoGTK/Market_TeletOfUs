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
TOFU_WORDS = {"tofu", "tofus", "tf", "tufo", "tufos", "tfc"}
ENERGY_WORDS = {"energia", "energias"}
STARDUST_WORDS = {"poeira", "poeiras"}
# "poeira"/"poeiras" so conta como moeda quando NAO vier seguido de "estelar" —
# nesse caso e o nome do item Poeira Estelar sendo vendido/descrito (quantidade,
# nao pagamento), ex "vendo 5 poeira estelar por 10 tofu" (5 = quantidade do item).
CURRENCY_PATTERN = (
    r"(gold|ouro|tofus?|tufos?|tfc|moedas?|coins?|energias?|poeiras?(?!\s+estelar)|"
    r"\btf\b|\bg\b|\bod\b|🪙|💰|💵|🧆|🧀|🔑|🗝️?|⚡|🔋|🌟)"
)
# a palavra "energia"/"energias" some daqui (direcao "moeda -> numero") —
# mensagens costumam usar "Energia" como TITULO/rotulo antes de uma quantidade
# ("⚡️ Energia (3x - ...)"), o que casava errado como "moeda energia = 3". Por
# extenso so conta como moeda vindo DEPOIS do numero ("300 energia"); o emoji
# continua valendo nas duas direcoes, que e inequivoco.
CURRENCY_PATTERN_REVERSED = (
    r"(gold|ouro|tofus?|tufos?|tfc|moedas?|coins?|poeiras?(?!\s+estelar)|"
    r"\btf\b|\bg\b|\bod\b|🪙|💰|💵|🧆|🧀|🔑|🗝️?|⚡|🔋|🌟)"
)
# mesma coisa, mas sem exigir fronteira de palavra ANTES da abreviacao — usada
# so na direcao "numero -> moeda", onde e comum o valor vir colado ("20tf",
# "50g", sem espaco). A fronteira DEPOIS continua exigida pra nao casar dentro
# de outra palavra qualquer.
CURRENCY_PATTERN_GLUED = (
    r"(gold|ouro|tofus?|tufos?|tfc|moedas?|coins?|energias?|poeiras?(?!\s+estelar)|"
    r"tf\b|g\b|od\b|🪙|💰|💵|🧆|🧀|🔑|🗝️?|⚡|🔋|🌟)"
)
# conector opcional entre o "k" (mil) e a moeda: "15k de ouro", "20k gold",
# "70k( apenas gold)", "**5" (markdown) — aceita espacos, parenteses,
# asteriscos de markdown e as palavras de ligacao em qualquer combinacao entre
# o numero e a moeda.
# "t" sozinho e usado por alguns jogadores como abreviacao muda de "tofu" logo
# antes do emoji 🧀 ("40t🧀", "15t 🧀") — entra como mais um token de ligacao.
# NAO inclui "/" de proposito: em listas tipo "70k/5🧀/15⚡" isso fazia o emoji
# de um preco "vazar" pro numero seguinte da lista (bug real, ja corrigido).
CONNECTOR = r"[\s()*:~]*(?:(?:de|apenas|s[oó]|t)[\s()*:~]*)*"

# marca de tier aprimorado, ex "65🧀 +1 180🧀" (preco base +1 preco do "+1")
TIER_MARKER_RE = re.compile(r"\+\s*\d+")

# marca de tabela de quantidade, ex "1x 5🧀 / 10x 45🧀" (preco unitario +
# preco no atacado) — o preco de mercado que interessa e o unitario (1x).
BULK_MARKER_RE = re.compile(r"\b1x\b", re.IGNORECASE)

# "Nk" sem moeda nenhuma do lado ("Martelo do gibby 80 k") — convencao da
# comunidade pra gold, ja que tofu/chave/energia raramente chegam na casa dos
# milhares. So usado como fallback quando nada mais casou (ver find_prices).
BARE_K_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*k\b", re.IGNORECASE)

PRICE_RE = re.compile(
    r"(\d+(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(k\b)?" + CONNECTOR + CURRENCY_PATTERN_GLUED,
    re.IGNORECASE,
)
PRICE_RE_REVERSED = re.compile(
    CURRENCY_PATTERN_REVERSED + CONNECTOR + r"[:\-]?\s*(\d+(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(k\b)?",
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
# diferentes do nome oficial, nao erro de digitacao/abreviacao) — checado
# junto com o resto do catalogo (substring direto), seguro porque sao frases
# de varias palavras, dificil aparecerem por acaso numa mensagem sobre outro
# item.
MANUAL_ALIASES = {
    "botas do sol": "boots_solar_step",
    "cajado da hydra a": "hydra_mag_staff",  # "A." = abreviacao de "Ancestral"
    "chave das minas": "chave_cripta",  # apelido informal da Chave da Cripta
    "chaves das minas": "chave_cripta",
}
MANUAL_ALIASES_NORM = {normalize(alias): key for alias, key in MANUAL_ALIASES.items()}

# apelidos de UMA PALAVRA SO que TAMBEM sao nome de moeda ("poeira", 🌟) — ao
# contrario dos de cima, so contam como FALLBACK, quando mais nada bateu na
# mensagem inteira. Sem essa guarda, uma mensagem tipo "compro anel por 5
# poeira" (pagando com poeira por OUTRO item) tambem "acharia" o item Poeira
# Estelar so por causa da palavra, virando 2 itens e quebrando um match que
# antes era limpo.
FALLBACK_WORD_ALIASES = {
    "poeira": "stardust",
    "energia": "energy_potion",
}
FALLBACK_WORD_ALIASES_NORM = {normalize(alias): key for alias, key in FALLBACK_WORD_ALIASES.items()}

# emoji usados como apelido pro item inteiro (sem nenhuma palavra do nome na
# mensagem) — normalize() remove todo emoji, entao isso e checado a parte, no
# texto original da linha. Mesma regra de fallback dos apelidos de palavra.
EMOJI_ITEM_ALIASES = {
    "🌟": "stardust",  # Poeira Estelar
}

# quando um item eh mencionado so pelo apelido curto ("poeira", 🌟) que
# TAMBEM e nome de moeda, o numero do lado e QUANTIDADE do item, nao preco
# naquela moeda (senao vira um item "custando ele mesmo"). Mapeia item -> moeda
# pra filtrar essa autorreferencia, seja o apelido por emoji ou por palavra.
ITEM_SELF_CURRENCY = {
    "stardust": "poeira",
    "energy_potion": "energia",
}


def currency_of(word):
    if word in ("🪙", "💰", "💵"):
        return "gold"
    if word in ("🧆", "🧀"):
        return "tofu"
    if word in ("🔑", "🗝️", "🗝"):
        return "chave"
    if word in ("⚡", "🔋"):
        return "energia"
    if word == "🌟":
        return "poeira"
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


# alguns nomes de item contem uma palavra que TAMBEM e nome de moeda ("Ovo de
# OURO", "Poção/Pacote de ENERGIA") — sem isso, "Ovo de Ouro - 12 tofu" lia
# "ouro" do proprio nome do item como se fosse a moeda gold. Mascara essas
# frases antes de procurar preco (a deteccao de item usa o texto original,
# sem essa mascara, entao nao afeta o reconhecimento do item em si).
PROTECTED_ITEM_PHRASES_RE = re.compile(
    r"ovo\s+de\s+ouro|(?:por?[çc](?:[aã]o|[oõ]es)|pacote|pote?s?)\s+de\s+energias?",
    re.IGNORECASE,
)


def find_prices(original_text):
    """Retorna lista de {"value": float, "currency": "gold"|"tofu"}, sem duplicatas."""
    original_text = PROTECTED_ITEM_PHRASES_RE.sub(" ", original_text)
    found = []
    # guarda o TRECHO (span) de cada simbolo/palavra de moeda ja usado num preco
    # "numero -> moeda". Isso impede que o mesmo emoji sirva DUAS vezes — uma
    # vez fechando um preco, outra vez "vazando" pra abrir o preco seguinte via
    # padrao reverso ("moeda -> numero"), que e como "5🧀 55.000💰" virava
    # "55.000 tofu" por engano alem do correto "55.000 gold".
    consumed_currency_spans = []
    # guarda tambem o trecho do NUMERO (com "k" se tiver) de cada preco ja
    # resolvido, pra saber quais "Nk" ainda estao "soltos" (ver BARE_K_RE).
    consumed_number_spans = []
    for m in PRICE_RE.finditer(original_text):
        val = parse_price_number(m.group(1), bool(m.group(2)))
        cur = currency_of(m.group(3))
        if val and cur:
            found.append({"value": val, "currency": cur})
            consumed_currency_spans.append(m.span(3))
            consumed_number_spans.append((m.start(1), m.end(2) if m.group(2) else m.end(1)))
    for m in PRICE_RE_REVERSED.finditer(original_text):
        cur_start, cur_end = m.span(1)
        if any(cur_start < e and cur_end > s for s, e in consumed_currency_spans):
            continue
        val = parse_price_number(m.group(2), bool(m.group(3)))
        cur = currency_of(m.group(1))
        if val and cur:
            found.append({"value": val, "currency": cur})
            consumed_number_spans.append((m.start(2), m.end(3) if m.group(3) else m.end(2)))

    # "Nk" sem NENHUMA moeda por perto (nao capturado pelos passes acima) e
    # convencao da comunidade pra gold ("Martelo do gibby 80 k" = 80 mil gold).
    # So conta se o "k" nao faz parte de um preco que ja foi resolvido com
    # outra moeda (senao ia duplicar/contradizer).
    for m in BARE_K_RE.finditer(original_text):
        span = m.span(0)
        if any(span[0] < e and span[1] > s for s, e in consumed_number_spans):
            continue
        val = parse_price_number(m.group(1), True)
        if val:
            found.append({"value": val, "currency": "gold"})

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
    if not items:
        for emoji, key in EMOJI_ITEM_ALIASES.items():
            if emoji in line:
                items = [(ITEMS_BY_KEY[key], 100)]
                break
    if not items:
        for alias_norm, key in FALLBACK_WORD_ALIASES_NORM.items():
            if alias_norm in norm:
                items = [(ITEMS_BY_KEY[key], 100)]
                break
    prices = find_prices(line)
    if len(items) == 1 and items[0][0]["key"] in ITEM_SELF_CURRENCY:
        self_currency = ITEM_SELF_CURRENCY[items[0][0]["key"]]
        prices = [p for p in prices if p["currency"] != self_currency]

    # "Item 65🧀 +1 180🧀": preco base e preco do item aprimorado ("+1") na
    # MESMA moeda — sao precos de coisas diferentes (tiers diferentes), entao
    # so aproveita o primeiro (base) e descarta o "+1", em vez de jogar tudo
    # pra revisao ou misturar os dois numa mediana sem sentido.
    if len(prices) == 2 and prices[0]["currency"] == prices[1]["currency"] and TIER_MARKER_RE.search(line):
        prices = [prices[0]]

    # "Item - 1x 5🧀 / 10x 45🧀": preco unitario e preco no atacado, mesma
    # moeda — fica so com o unitario (1x), que e o que representa o preco de
    # mercado do item avulso.
    if len(prices) == 2 and prices[0]["currency"] == prices[1]["currency"] and BULK_MARKER_RE.search(line):
        prices = [prices[0]]

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
