"""
Puxa o historico de mensagens do topico/canal de vendas e salva em raw_messages.jsonl.
Roda UMA vez pra pegar o passado; dai em diante use monitor_live.py pra acompanhar
as mensagens novas.

Primeira execucao pede o codigo de login que chega no seu Telegram/SMS —
isso cria um arquivo market_session.session que autentica as proximas execucoes
sem pedir codigo de novo.

Uso: python fetch_history.py            (pega TODO o historico)
     python fetch_history.py --days 60  (so os ultimos 60 dias)
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon.sync import TelegramClient

import config

OUT_PATH = Path(__file__).parent / "raw_messages.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None, help="limitar aos ultimos N dias (default: historico completo)")
    args = parser.parse_args()

    seen_ids = set()
    if OUT_PATH.exists():
        for line in OUT_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                seen_ids.add(json.loads(line)["id"])

    kwargs = {"reverse": True}
    if args.days:
        kwargs["offset_date"] = datetime.now(timezone.utc) - timedelta(days=args.days)
    topic_id = getattr(config, "TOPIC_ID", None)
    if topic_id:
        kwargs["reply_to"] = topic_id

    count = 0
    with TelegramClient("market_session", config.API_ID, config.API_HASH) as client:
        entity = client.get_entity(config.CHAT)
        with OUT_PATH.open("a", encoding="utf-8") as f:
            for msg in client.iter_messages(entity, **kwargs):
                if not msg.text:
                    continue
                if msg.id in seen_ids:
                    continue
                record = {
                    "id": msg.id,
                    "date": msg.date.isoformat(),
                    "sender_id": msg.sender_id,
                    "text": msg.text,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                seen_ids.add(msg.id)
                count += 1
                if count % 200 == 0:
                    print(f"...{count} mensagens salvas ate agora")

    print(f"Salvas {count} mensagens novas em {OUT_PATH}")


if __name__ == "__main__":
    main()
