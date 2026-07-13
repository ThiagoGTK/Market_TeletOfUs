# Copie este arquivo para config.py e preencha com seus dados.
# NUNCA suba config.py pro git nem compartilhe — ele guarda credenciais da sua conta.

# 1. Vá em https://my.telegram.org/apps, faça login com seu numero,
#    crie um app qualquer (nome/plataforma nao importam) e copie:
API_ID = 123456
API_HASH = "sua_api_hash_aqui"

# 2. Numero de telefone da conta que é membro do grupo (formato internacional)
PHONE = "+55XXXXXXXXXXX"

# 3. Identificador do canal/grupo onde rolam as vendas.
#    Pode ser o @username publico (ex: "meugrupo_trades"),
#    ou o ID numerico do chat/topico (descubra rodando list_chats.py).
CHAT = "@username_do_canal_de_vendas"

# Se o canal de vendas for um topico dentro de um grupo com Topics ativado,
# preencha o ID do topico aqui (ou deixe None se for um chat/canal normal)
TOPIC_ID = None
