"""
Lista os grupos/canais da sua conta, pra você achar o identificador certo
do canal onde rolam as vendas (usado no CHAT do config.py).

Rode: python list_chats.py
Na primeira vez vai pedir o código de login que chega no seu Telegram.
Salva o resultado em chats.txt (em UTF-8, pra nao quebrar com emoji).
"""
from pathlib import Path

from telethon.sync import TelegramClient
import config

OUT_PATH = Path(__file__).parent / "chats.txt"

lines = []
with TelegramClient("market_session", config.API_ID, config.API_HASH) as client:
    total = 0
    groups = 0
    for archived in (False, True):
        for dialog in client.iter_dialogs(limit=500, archived=archived):
            total += 1
            kind = "canal" if dialog.is_channel else ("grupo" if dialog.is_group else "usuario")
            if kind != "usuario":
                groups += 1
            tag = "[arquivado] " if archived else ""
            lines.append(f"{tag}[{kind:8}] {dialog.name!r:50} id={dialog.id}  username={getattr(dialog.entity, 'username', None)}")

    lines.append(f"\nTotal de dialogos: {total}  (grupos/canais: {groups})")

OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Salvo em {OUT_PATH} ({total} dialogos, {groups} grupos/canais)")
