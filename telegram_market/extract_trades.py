"""
Le raw_messages.jsonl, tenta reconhecer item + preco (por linha, quando a
mensagem lista varios itens) e separa em:
  - trades.jsonl        pares item+preco confiaveis
  - review_needed.csv   trechos ambiguos (0 ou 2+ itens, ou preco faltando)
    pra voce revisar/corrigir a mao e (opcionalmente) reincluir manualmente.

Uso: python extract_trades.py
"""
import csv
import json
from pathlib import Path

from matching import analyze_message

RAW_PATH = Path(__file__).parent / "raw_messages.jsonl"
TRADES_PATH = Path(__file__).parent / "trades.jsonl"
REVIEW_PATH = Path(__file__).parent / "review_needed.csv"


def main():
    if not RAW_PATH.exists():
        print("raw_messages.jsonl nao existe ainda — rode fetch_history.py primeiro.")
        return

    trades = []
    review_rows = []
    skipped_noise = 0

    for line in RAW_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        analysis = analyze_message(rec["text"])

        if analysis is None:
            skipped_noise += 1
            continue

        for t in analysis["trades"]:
            trades.append({
                "msg_id": rec["id"],
                "date": rec["date"],
                "sender_id": rec["sender_id"],
                "item_key": t["item_key"],
                "item_name": t["item_name"],
                "price": t["price"],
                "currency": t["currency"],
                "raw_text": t["line"],
            })

        for l in analysis["leftover"]:
            review_rows.append({
                "msg_id": rec["id"],
                "date": rec["date"],
                "items_found": "; ".join(i["name"] for i in l["items"]),
                "prices_found": "; ".join(f"{p['value']} {p['currency']}" for p in l["prices"]),
                "text": l["text"],
            })

    TRADES_PATH.write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in trades) + ("\n" if trades else ""),
        encoding="utf-8",
    )

    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "date", "items_found", "prices_found", "text"])
        writer.writeheader()
        writer.writerows(review_rows)

    print(f"{skipped_noise} mensagens de sistema/bot descartadas")
    print(f"{len(trades)} trades confiaveis -> {TRADES_PATH}")
    print(f"{len(review_rows)} trechos ambiguos pra revisar -> {REVIEW_PATH}")


if __name__ == "__main__":
    main()
