"""
Agrega trades.jsonl num preco de mercado por item **e por moeda** (gold e tofu
sao tratados separadamente, ja que tem escalas totalmente diferentes) e escreve
market_prices.json. Rode isso quando quiser recalcular os precos (ex: depois de
1 mes de coleta, ou sempre que quiser atualizar).

Uso: python compute_prices.py                (usa todo o historico coletado)
     python compute_prices.py --days 30       (so os ultimos 30 dias)
"""
import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRADES_PATH = Path(__file__).parent / "trades.jsonl"
OUT_PATH = Path(__file__).parent / "market_prices.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None, help="considerar so trades dos ultimos N dias (default: tudo)")
    args = parser.parse_args()

    if not TRADES_PATH.exists():
        print("trades.jsonl nao existe ainda — rode extract_trades.py primeiro.")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None
    by_item = defaultdict(lambda: defaultdict(list))

    for line in TRADES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        t = json.loads(line)
        if cutoff:
            date = datetime.fromisoformat(t["date"])
            if date < cutoff:
                continue
        by_item[t["item_key"]][t.get("currency", "gold")].append(t["price"])

    result = {}
    for key, by_currency in by_item.items():
        entry = {}
        for currency, prices in by_currency.items():
            entry[currency] = {
                "median": statistics.median(prices),
                "avg": round(statistics.mean(prices), 2),
                "min": min(prices),
                "max": max(prices),
                "samples": len(prices),
            }
        result[key] = entry

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    window = f"ultimos {args.days} dias" if args.days else "todo o historico"
    print(f"Precos calculados para {len(result)} itens ({window}) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
