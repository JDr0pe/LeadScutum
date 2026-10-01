from typing import Optional
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import sqlite3

from database import init_db, DB_NAME
from engine import processar_lead, consultar

# Garante que a tabela de auditoria existe
init_db()

app = FastAPI(title="LeadScutum API", version="2.6.0")

class ConsultaPayload(BaseModel):
    tipo: str = Field(default="auto", description="Tipo de consulta: 'nome', 'cpf', 'cnpj' ou 'auto'")
    valor: str = Field(..., min_length=1, description="Termo a ser consultado (Nome, CPF ou CNPJ)")

class LeadPayload(BaseModel):
    nome: Optional[str] = Field(default="", description="Nome Completo ou Razão Social")
    documento: Optional[str] = Field(default="", description="CPF ou CNPJ")
    email: Optional[str] = Field(default="", description="E-mail de contato")
    valor: Optional[float] = Field(default=0.0, ge=0.0, description="Volume financeiro estimado")

@app.post("/api/consultar")
def api_consultar(payload: ConsultaPayload):
    """
    Endpoint para consulta direta somente por Nome, CNPJ ou CPF.
    Não requer cadastro de e-mail ou valor.
    """
    return consultar(payload.tipo, payload.valor)

@app.get("/api/consultar")
def api_consultar_get(
    tipo: str = "auto",
    q: Optional[str] = None,
    valor: Optional[str] = None,
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    cnpj: Optional[str] = None,
):
    """
    Consulta direta via GET para testes rápidos ou integrações URL.
    """
    if cpf:
        return consultar("cpf", cpf)
    if cnpj:
        return consultar("cnpj", cnpj)
    if nome:
        return consultar("nome", nome)
    termo = valor or q or ""
    if not termo:
        return {"status": "ERRO", "mensagem": "Informe ao menos um termo para consulta ('q', 'nome', 'cpf' ou 'cnpj')."}
    return consultar(tipo, termo)

@app.post("/api/processar-lead")
def api_processar(lead: LeadPayload):
    """
    Processa entrada na esteira de leads, aceitando apenas documento, apenas nome ou ambos.
    """
    return processar_lead(lead.nome, lead.documento, lead.email, lead.valor)

@app.get("/api/leads")
def api_listar():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, tipo_doc, documento, email, valor_previsto, status_risco, detalhes_risco, destino, data_criacao 
            FROM leads 
            ORDER BY id DESC 
            LIMIT 50
        """)
        return cur.fetchall()

@app.get("/")
def index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")