import os
import re
from typing import Optional
from dotenv import load_dotenv
import mailtrap as mt

# Carrega variáveis do arquivo .env
load_dotenv()

MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN", "").strip()
MAILTRAP_SENDER_EMAIL = os.getenv("MAILTRAP_SENDER_EMAIL", "hello@demomailtrap.co").strip()
MAILTRAP_SENDER_NAME = os.getenv("MAILTRAP_SENDER_NAME", "LeadScutum Compliance").strip()

def extrair_texto_puro(html: str) -> str:
    """Remove tags HTML para gerar uma versão em texto simples do e-mail."""
    if not html:
        return ""
    texto = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", texto).strip()

def enviar_email(
    destinatario: str, 
    assunto: str, 
    html_corpo: str, 
    categoria: str = "Compliance Alert"
) -> bool:
    """
    Dispara e-mail via API do Mailtrap usando o SDK oficial (mailtrap).
    Lê as credenciais diretamente do arquivo .env.
    Se MAILTRAP_API_TOKEN estiver vazio, simula o envio no console.
    """
    email_destino = (destinatario or "").strip()
    if not email_destino:
        print("[MAILER] Erro: destinatário não informado.")
        return False

    # Modo simulação quando o token não foi configurado no .env
    if not MAILTRAP_API_TOKEN or MAILTRAP_API_TOKEN == "<YOUR_API_TOKEN>":
        print("\n" + "="*55)
        print("[NOTIFICAÇÃO DESPACHADA (SIMULAÇÃO NO CONSOLE)]")
        print(f"Para: {email_destino}")
        print(f"Assunto: {assunto}")
        print(f"Categoria: {categoria}")
        print("Dica: Para disparo real via Mailtrap, configure seu 'MAILTRAP_API_TOKEN' no arquivo .env")
        print("="*55 + "\n")
        return True

    try:
        mail = mt.Mail(
            sender=mt.Address(email=MAILTRAP_SENDER_EMAIL, name=MAILTRAP_SENDER_NAME),
            to=[mt.Address(email=email_destino)],
            subject=assunto,
            text=extrair_texto_puro(html_corpo),
            html=html_corpo,
            category=categoria,
        )

        client = mt.MailtrapClient(token=MAILTRAP_API_TOKEN)
        response = client.send(mail)
        print(f"[MAILTRAP ENVIADO COM SUCESSO] Para: {email_destino} | Resposta: {response}")
        return True

    except Exception as e:
        print(f"[ERRO NO ENVIO MAILTRAP]: {e}")
        return False