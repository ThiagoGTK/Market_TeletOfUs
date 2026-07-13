"""
Lista os topicos (forum topics) do grupo configurado em CHAT no config.py,
pra voce achar o TOPIC_ID do topico de vendas.

Rode: python list_topics.py
Salva o resultado em topics.txt (UTF-8).
"""
from pathlib import Path

from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetForumTopicsRequest

import config

OUT_PATH = Path(__file__).parent / "topics.txt"

lines = []
with TelegramClient("market_session", config.API_ID, config.API_HASH) as client:
    entity = client.get_entity(config.CHAT)
    result = client(GetForumTopicsRequest(
        peer=entity,
        offset_date=None,
        offset_id=0,
        offset_topic=0,
        limit=100,
    ))
    for topic in result.topics:
        lines.append(f"id={topic.id:<10} titulo={topic.title!r}")

OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Salvo em {OUT_PATH} ({len(result.topics)} topicos)")
