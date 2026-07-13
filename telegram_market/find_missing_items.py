"""
Vasculha review_needed.csv atras de linhas que tem preco reconhecido mas
NENHUM item reconhecido — ou seja, provavelmente um item que nao esta em
items_final.json. Agrupa por nome "adivinhado" (tira emoji/preco/moeda da
linha) e mostra os mais frequentes, pra decidir se vale cadastrar.

Uso: python find_missing_items.py
"""
import csv
import re
from collections import Counter
from pathlib import Path

from matching import EMOJI_RE, PRICE_RE, PRICE_RE_REVERSED

REVIEW_PATH = Path(__file__).parent / "review_needed.csv"
OUT_PATH = Path(__file__).parent / "missing_items.txt"

STRIP_WORDS_RE = re.compile(
    r"\b(vendo|compro|troco|venda|compra|cada|apenas|somente|barato|promo[cç][aã]o|"
    r"por|de|ou|pago|preço|pre[cç]o|x\d+|\d+x)\b",
    re.IGNORECASE,
)


def guess_name(text):
    t = EMOJI_RE.sub(" ", text)
    t = PRICE_RE.sub(" ", t)
    t = PRICE_RE_REVERSED.sub(" ", t)
    t = re.sub(r"[\-=:•~_*\[\]()]", " ", t)
    t = STRIP_WORDS_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip(" .!\"'")
    return t


def main():
    counter = Counter()
    example_price = {}

    with REVIEW_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["items_found"]:
                continue
            if not row["prices_found"]:
                continue
            name = guess_name(row["text"])
            if len(name) < 3 or len(name) > 40:
                continue
            counter[name.lower()] += 1
            example_price.setdefault(name.lower(), row["prices_found"])

    lines = [f"{count:4}x  {name!r}  (ex. preco: {example_price[name]})"
             for name, count in counter.most_common(80)]
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(counter)} nomes candidatos distintos -> {OUT_PATH}")


if __name__ == "__main__":
    main()
