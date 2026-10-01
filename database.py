import sqlite3

DB_NAME = "compliance_leads.db"

def init_db():
    """Cria a tabela de trilha de auditoria para registros dos leads."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo_doc TEXT NOT NULL,
                documento TEXT NOT NULL,
                email TEXT NOT NULL,
                valor_previsto REAL,
                status_risco TEXT NOT NULL,
                detalhes_risco TEXT,
                destino TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def salvar_lead(
    nome: str, 
    tipo_doc: str, 
    documento: str, 
    email: str, 
    valor: float, 
    status_risco: str, 
    detalhes: str, 
    destino: str
) -> int:
    """Grava a decisão regulatória e devolve o ID único da requisição."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (nome, tipo_doc, documento, email, valor_previsto, status_risco, detalhes_risco, destino)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(nome or "Não informado"), 
            str(tipo_doc or "NOME"), 
            str(documento or "N/A"), 
            str(email or "N/A"), 
            float(valor or 0.0), 
            str(status_risco or "NEGATIVO"), 
            str(detalhes or ""), 
            str(destino or "comercial@empresa.com")
        ))
        conn.commit()
        return cursor.lastrowid