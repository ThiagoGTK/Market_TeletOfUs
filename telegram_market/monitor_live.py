"""
Fica escutando o canal/grupo de vendas em tempo real e vai salvando cada
mensagem nova em raw_messages.jsonl. Deixe rodando em background
(ex: numa janela de terminal separada, ou como tarefa agendada).

Usa a sessao ja autenticada por fetch_history.py ou list_chats.py —
rode um deles primeiro pra fazer o login unico.

Uso: python monitor_live.py
Pra parar: Ctrl+C
"""
import json
from pathlib import Path

from telethon import events
from telethon.sync import TelegramClient

import config

OUT_PATH = Path(__file__).parent / "raw_messages.jsonl"

client = TelegramClient("market_session", config.API_ID, config.API_HASH)


@client.on(events.NewMessage(chats=config.CHAT))
async def handler(event):
    msg = event.message
    if not msg.text:
        return
    if getattr(config, "TOPIC_ID", None) and msg.reply_to and msg.reply_to.reply_to_top_id != config.TOPIC_ID:
        return
    record = {
        "id": msg.id,
        "date": msg.date.isoformat(),
        "sender_id": msg.sender_id,
        "text": msg.text,
    }
    with OUT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[nova mensagem] {msg.text[:80]!r}")


print(f"Escutando {config.CHAT}... (Ctrl+C pra parar)")
with client:
    client.run_until_disconnected()
