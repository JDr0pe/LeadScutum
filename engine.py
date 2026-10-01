import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import duckdb
from validate_docbr import CPF, CNPJ
from database import salvar_lead
from mailer import enviar_email

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DUCKDB_PATH = str(BASE_DIR / "dados.duckdb")

EMAIL_DESTINO_COMERCIAL = os.getenv("EMAIL_DESTINO_COMERCIAL", "comercial@empresa.com").strip()
EMAIL_DESTINO_JURIDICO = os.getenv("EMAIL_DESTINO_JURIDICO", "juridico@empresa.com").strip()

# Mapeamento oficial de qualificações societárias da Receita Federal
QUALIFICACOES_SOCIOS = {
    "05": "Administrador",
    "08": "Conselheiro de Administração",
    "10": "Diretor",
    "16": "Presidente",
    "20": "Sociedade Consorciada",
    "22": "Sócio",
    "23": "Sócio Capitalista",
    "24": "Sócio Comanditado",
    "25": "Sócio Comanditário",
    "26": "Sócio de Indústria",
    "28": "Sócio Ostensivo",
    "29": "Sócio Pessoa Jurídica Domiciliada no Exterior",
    "30": "Diretor Presidente",
    "37": "Sócio Pessoa Física Residente no Exterior",
    "47": "Sócio Incapaz ou Inabilitado",
    "48": "Sócio Menor (Assistido/Representado)",
    "49": "Sócio-Administrador",
    "52": "Sócio com Capital",
    "53": "Sócio sem Capital",
    "54": "Fundador",
    "59": "Produtor Rural",
    "63": "Cotas em Tesouraria",
    "65": "Titular de Empresa Individual",
    "66": "Sócio Cooperado",
}

def normalizar(doc: Optional[str]) -> str:
    """Remove caracteres não numéricos."""
    if not doc:
        return ""
    return re.sub(r"\D", "", str(doc))

def extrair_mascara_cpf(doc: str) -> str:
    """Retorna máscara no padrão CGU (***.XXX.XXX-**) a partir de CPF."""
    limpo = normalizar(doc)
    if len(limpo) == 11:
        return f"***.{limpo[3:6]}.{limpo[6:9]}-**"
    elif len(limpo) == 6:
        return f"***.{limpo[:3]}.{limpo[3:]}-**"
    elif "***" in doc:
        digitos = normalizar(doc)
        if len(digitos) == 6:
            return f"***.{digitos[:3]}.{digitos[3:]}-**"
    return doc.strip()

def consultar_cpf(cpf_input: str) -> Dict[str, Any]:
    """
    Consulta se o CPF informado consta na base de PEPs (CGU).
    Cruza também com o QSA para identificar empresas onde o PEP é sócio.
    """
    t0 = time.time()
    cpf_limpo = normalizar(cpf_input)
    val_cpf = CPF()

    aviso_dv = None
    if len(cpf_limpo) == 11 and not val_cpf.validate(cpf_limpo):
        aviso_dv = "Dígitos verificadores do CPF não conferem matematicamente, mas a busca foi realizada na base de PEP."

    mascara = extrair_mascara_cpf(cpf_input)
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        # Busca exata pelo CPF mascarado padrão da CGU
        query = """
            SELECT cpf, nome_pep, sigla_funcao, descricao_funcao, nivel_funcao, nome_orgao, 
                   data_inicio_exercicio, data_fim_exercicio, data_fim_carencia 
            FROM pep 
            WHERE cpf = ?
            ORDER BY data_fim_exercicio DESC
        """
        rows = con.execute(query, [mascara]).fetchall()

        # Se não achou pela máscara exata e temos 6 ou 11 dígitos, busca pelos 6 dígitos intermediários
        if not rows and len(cpf_limpo) in (6, 11):
            digitos_6 = cpf_limpo[3:9] if len(cpf_limpo) == 11 else cpf_limpo
            query_digits = """
                SELECT cpf, nome_pep, sigla_funcao, descricao_funcao, nivel_funcao, nome_orgao, 
                       data_inicio_exercicio, data_fim_exercicio, data_fim_carencia 
                FROM pep 
                WHERE regexp_replace(cpf, '[^0-9]', '', 'g') = ?
                ORDER BY data_fim_exercicio DESC
            """
            rows = con.execute(query_digits, [digitos_6]).fetchall()

        registros_pep = []
        for r in rows:
            registros_pep.append({
                "cpf_mascarado": r[0],
                "nome_pep": r[1],
                "sigla_funcao": r[2],
                "descricao_funcao": r[3] or r[2] or "Não especificado",
                "nivel_funcao": r[4],
                "nome_orgao": r[5],
                "data_inicio_exercicio": r[6],
                "data_fim_exercicio": r[7],
                "data_fim_carencia": r[8]
            })

        vinculos_empresas = []
        if registros_pep:
            cpfs_encontrados = list({r["cpf_mascarado"] for r in registros_pep})
            placeholders = ",".join(["?"] * len(cpfs_encontrados))
            query_vinculos = f"""
                SELECT pep_cpf, cnpj_basico, razao_social, qualificacao_socio, data_entrada_sociedade
                FROM vw_pep_socios_empresas 
                WHERE pep_cpf IN ({placeholders})
            """
            v_rows = con.execute(query_vinculos, cpfs_encontrados).fetchall()
            for v in v_rows:
                vinculos_empresas.append({
                    "pep_cpf": v[0],
                    "cnpj_basico": v[1],
                    "razao_social": v[2] or f"CNPJ Básico {v[1]}",
                    "qualificacao_codigo": v[3],
                    "qualificacao_desc": QUALIFICACOES_SOCIOS.get(v[3], f"Qualificação {v[3]}"),
                    "data_entrada_sociedade": v[4]
                })

        t1 = time.time()
        tempo_ms = round((t1 - t0) * 1000, 2)

        if registros_pep:
            primeiro = registros_pep[0]
            detalhe_str = f"PEP Identificado: {primeiro['nome_pep']} | Função: {primeiro['descricao_funcao']} ({primeiro['nome_orgao']})"
            if vinculos_empresas:
                detalhe_str += f" | Sócio na empresa: {vinculos_empresas[0]['razao_social']}"

            return {
                "status": "SUCESSO",
                "tipo_consulta": "CPF",
                "termo_buscado": cpf_input,
                "risco": "POSITIVO",
                "mensagem": detalhe_str,
                "total_ocorrencias": len(registros_pep),
                "peps": registros_pep,
                "vinculos": vinculos_empresas,
                "aviso": aviso_dv,
                "tempo_ms": tempo_ms
            }
        else:
            return {
                "status": "SUCESSO",
                "tipo_consulta": "CPF",
                "termo_buscado": cpf_input,
                "risco": "NEGATIVO",
                "mensagem": "Sem apontamentos de PEP identificados no CPF informado na base DuckDB.",
                "total_ocorrencias": 0,
                "peps": [],
                "vinculos": [],
                "aviso": aviso_dv,
                "tempo_ms": tempo_ms
            }
    except Exception as e:
        return {
            "status": "ERRO",
            "tipo_consulta": "CPF",
            "termo_buscado": cpf_input,
            "risco": "POSITIVO",
            "mensagem": f"Erro na consulta DuckDB: {str(e)}",
            "peps": [],
            "vinculos": [],
            "tempo_ms": round((time.time() - t0) * 1000, 2)
        }
    finally:
        con.close()

def consultar_cnpj(cnpj_input: str) -> Dict[str, Any]:
    """
    Consulta empresa pelo CNPJ e verifica se há sócios apontados como PEP no QSA.
    """
    t0 = time.time()
    cnpj_limpo = normalizar(cnpj_input)
    val_cnpj = CNPJ()

    aviso_dv = None
    if len(cnpj_limpo) == 14 and not val_cnpj.validate(cnpj_limpo):
        aviso_dv = "Dígitos verificadores do CNPJ são matematicamente inválidos, mas a consulta no QSA colunar foi efetuada."

    cnpj_basico = cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else cnpj_limpo
    if len(cnpj_basico) < 8:
        return {
            "status": "ERRO",
            "tipo_consulta": "CNPJ",
            "termo_buscado": cnpj_input,
            "risco": "ERRO",
            "mensagem": "CNPJ deve possuir pelo menos os 8 dígitos do CNPJ básico.",
            "tempo_ms": 0.0
        }

    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        # 1. Informações cadastrais da empresa
        empresa_row = con.execute("""
            SELECT razao_social, natureza_juridica, porte_empresa, capital_social
            FROM empresas 
            WHERE cnpj_basico = ? 
            LIMIT 1
        """, [cnpj_basico]).fetchone()

        empresa_info = None
        if empresa_row:
            empresa_info = {
                "cnpj_basico": cnpj_basico,
                "razao_social": empresa_row[0],
                "natureza_juridica": empresa_row[1],
                "porte": empresa_row[2],
                "capital_social": empresa_row[3]
            }

        # 2. Sócios PEP identificados na empresa
        socios_pep_rows = con.execute("""
            SELECT pep_cpf, nome_pep, pep_sigla_funcao, pep_funcao, pep_orgao, 
                   pep_inicio_exercicio, pep_fim_exercicio, qualificacao_socio, data_entrada_sociedade
            FROM vw_pep_socios_empresas
            WHERE cnpj_basico = ?
        """, [cnpj_basico]).fetchall()

        socios_pep = []
        nomes_pep_set = set()
        for s in socios_pep_rows:
            nomes_pep_set.add(s[1].upper() if s[1] else "")
            socios_pep.append({
                "pep_cpf": s[0],
                "nome_socio": s[1],
                "sigla_funcao": s[2],
                "descricao_funcao": s[3] or s[2] or "PEP",
                "orgao": s[4],
                "inicio_exercicio": s[5],
                "fim_exercicio": s[6],
                "qualificacao_codigo": s[7],
                "qualificacao_desc": QUALIFICACOES_SOCIOS.get(s[7], f"Qualificação {s[7]}"),
                "data_entrada_sociedade": s[8]
            })

        # 3. Lista completa do QSA da empresa
        todos_socios_rows = con.execute("""
            SELECT nome_socio, qualificacao_socio, cnpj_cpf_socio, data_entrada_sociedade, faixa_etaria
            FROM socios 
            WHERE cnpj_basico = ?
        """, [cnpj_basico]).fetchall()

        qsa = []
        for s in todos_socios_rows:
            nome = s[0] or "NÃO INFORMADO"
            is_pep = nome.upper() in nomes_pep_set
            qsa.append({
                "nome": nome,
                "qualificacao_codigo": s[1],
                "qualificacao_desc": QUALIFICACOES_SOCIOS.get(s[1], f"Qualificação {s[1]}"),
                "documento_mascarado": s[2],
                "data_entrada": s[3],
                "faixa_etaria": s[4],
                "is_pep": is_pep
            })

        t1 = time.time()
        tempo_ms = round((t1 - t0) * 1000, 2)

        if socios_pep:
            primeiro = socios_pep[0]
            razao = empresa_info["razao_social"] if empresa_info else f"CNPJ {cnpj_basico}"
            detalhe_str = f"Sócio PEP Identificado no QSA: {primeiro['nome_socio']} ({primeiro['qualificacao_desc']}) | Vínculo: {primeiro['descricao_funcao']} - {primeiro['orgao']}"
            return {
                "status": "SUCESSO",
                "tipo_consulta": "CNPJ",
                "termo_buscado": cnpj_input,
                "cnpj_basico": cnpj_basico,
                "risco": "POSITIVO",
                "mensagem": detalhe_str,
                "empresa": empresa_info,
                "total_socios_pep": len(socios_pep),
                "socios_pep": socios_pep,
                "qsa": qsa,
                "aviso": aviso_dv,
                "tempo_ms": tempo_ms
            }
        else:
            msg = "CNPJ regular. Nenhum sócio do QSA identificado com restrição PEP."
            if not empresa_info and not qsa:
                msg = "CNPJ sem registros na base de empresas/sócios colunar (nenhum sócio PEP associado)."
            return {
                "status": "SUCESSO",
                "tipo_consulta": "CNPJ",
                "termo_buscado": cnpj_input,
                "cnpj_basico": cnpj_basico,
                "risco": "NEGATIVO",
                "mensagem": msg,
                "empresa": empresa_info,
                "total_socios_pep": 0,
                "socios_pep": [],
                "qsa": qsa,
                "aviso": aviso_dv,
                "tempo_ms": tempo_ms
            }
    except Exception as e:
        return {
            "status": "ERRO",
            "tipo_consulta": "CNPJ",
            "termo_buscado": cnpj_input,
            "risco": "POSITIVO",
            "mensagem": f"Erro na consulta DuckDB: {str(e)}",
            "tempo_ms": round((time.time() - t0) * 1000, 2)
        }
    finally:
        con.close()

def consultar_nome(nome_input: str) -> Dict[str, Any]:
    """
    Consulta PEPs por nome de pessoa física ou razão social de empresa com sócio PEP.
    Utiliza strip_accents e busca case-insensitive no DuckDB.
    """
    t0 = time.time()
    nome_limpo = (nome_input or "").strip()
    if len(nome_limpo) < 2:
        return {
            "status": "ERRO",
            "tipo_consulta": "NOME",
            "termo_buscado": nome_input,
            "risco": "ERRO",
            "mensagem": "Nome para busca deve possuir pelo menos 2 caracteres.",
            "tempo_ms": 0.0
        }

    termo_like = f"%{nome_limpo}%"
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        # 1. Busca na base de PEPs (Pessoas Físicas)
        pep_rows = con.execute("""
            SELECT cpf, nome_pep, sigla_funcao, descricao_funcao, nivel_funcao, nome_orgao, 
                   data_inicio_exercicio, data_fim_exercicio, data_fim_carencia 
            FROM pep 
            WHERE strip_accents(upper(nome_pep)) LIKE strip_accents(upper(?))
            ORDER BY data_fim_exercicio DESC
            LIMIT 50
        """, [termo_like]).fetchall()

        registros_pep = []
        for r in pep_rows:
            registros_pep.append({
                "cpf_mascarado": r[0],
                "nome_pep": r[1],
                "sigla_funcao": r[2],
                "descricao_funcao": r[3] or r[2] or "Não especificado",
                "nivel_funcao": r[4],
                "nome_orgao": r[5],
                "data_inicio_exercicio": r[6],
                "data_fim_exercicio": r[7],
                "data_fim_carencia": r[8]
            })

        # 2. Vínculos societários para os PEPs encontrados
        vinculos_map = {}
        if registros_pep:
            cpfs = list({r["cpf_mascarado"] for r in registros_pep})
            placeholders = ",".join(["?"] * len(cpfs))
            v_rows = con.execute(f"""
                SELECT pep_cpf, cnpj_basico, razao_social, qualificacao_socio, data_entrada_sociedade
                FROM vw_pep_socios_empresas 
                WHERE pep_cpf IN ({placeholders})
            """, cpfs).fetchall()
            for v in v_rows:
                vinculos_map.setdefault(v[0], []).append({
                    "cnpj_basico": v[1],
                    "razao_social": v[2] or f"CNPJ Básico {v[1]}",
                    "qualificacao_codigo": v[3],
                    "qualificacao_desc": QUALIFICACOES_SOCIOS.get(v[3], f"Qualificação {v[3]}"),
                    "data_entrada_sociedade": v[4]
                })

        for p in registros_pep:
            p["vinculos"] = vinculos_map.get(p["cpf_mascarado"], [])

        # 3. Busca também em Razão Social de empresas com sócios PEP
        empresas_com_pep = []
        if not registros_pep or len(registros_pep) < 10:
            e_rows = con.execute("""
                SELECT cnpj_basico, razao_social, pep_cpf, nome_pep, pep_funcao, pep_orgao, qualificacao_socio
                FROM vw_pep_socios_empresas
                WHERE strip_accents(upper(razao_social)) LIKE strip_accents(upper(?))
                LIMIT 15
            """, [termo_like]).fetchall()
            for e in e_rows:
                empresas_com_pep.append({
                    "cnpj_basico": e[0],
                    "razao_social": e[1],
                    "pep_cpf": e[2],
                    "nome_socio_pep": e[3],
                    "cargo_pep": e[4],
                    "orgao_pep": e[5],
                    "qualificacao_socio": QUALIFICACOES_SOCIOS.get(e[6], f"Qualificação {e[6]}")
                })

        t1 = time.time()
        tempo_ms = round((t1 - t0) * 1000, 2)

        total_encontrados = len(registros_pep) + len(empresas_com_pep)
        if total_encontrados > 0:
            if registros_pep:
                primeiro = registros_pep[0]
                detalhe_str = f"PEP Identificado por Nome: {primeiro['nome_pep']} | Função: {primeiro['descricao_funcao']} ({primeiro['nome_orgao']})"
                if len(registros_pep) > 1:
                    detalhe_str += f" (+ {len(registros_pep)-1} outro(s) registro(s))"
            else:
                primeiro_e = empresas_com_pep[0]
                detalhe_str = f"Empresa com sócio PEP identificada: {primeiro_e['razao_social']} | Sócio PEP: {primeiro_e['nome_socio_pep']} ({primeiro_e['cargo_pep']})"

            return {
                "status": "SUCESSO",
                "tipo_consulta": "NOME",
                "termo_buscado": nome_input,
                "risco": "POSITIVO",
                "mensagem": detalhe_str,
                "total_ocorrencias": total_encontrados,
                "peps": registros_pep,
                "empresas_com_pep": empresas_com_pep,
                "tempo_ms": tempo_ms
            }
        else:
            return {
                "status": "SUCESSO",
                "tipo_consulta": "NOME",
                "termo_buscado": nome_input,
                "risco": "NEGATIVO",
                "mensagem": f"Nenhum apontamento PEP identificado para o nome '{nome_input}'.",
                "total_ocorrencias": 0,
                "peps": [],
                "empresas_com_pep": [],
                "tempo_ms": tempo_ms
            }
    except Exception as e:
        return {
            "status": "ERRO",
            "tipo_consulta": "NOME",
            "termo_buscado": nome_input,
            "risco": "POSITIVO",
            "mensagem": f"Erro na consulta DuckDB: {str(e)}",
            "peps": [],
            "tempo_ms": round((time.time() - t0) * 1000, 2)
        }
    finally:
        con.close()

def consultar(tipo: str, valor: str) -> Dict[str, Any]:
    """
    Roteador unificado de consulta: 'nome', 'cpf', 'cnpj' ou 'auto'.
    """
    tipo_norm = (tipo or "").strip().lower()
    valor_limpo = (valor or "").strip()
    digits = normalizar(valor_limpo)

    if tipo_norm == "auto" or not tipo_norm:
        if len(digits) == 14:
            tipo_norm = "cnpj"
        elif len(digits) == 11:
            tipo_norm = "cpf"
        elif len(digits) == 8 and (valor_limpo.isdigit() or "/" in valor_limpo or "." in valor_limpo):
            tipo_norm = "cnpj"
        elif "***" in valor_limpo or len(digits) == 6:
            tipo_norm = "cpf"
        else:
            tipo_norm = "nome"

    if tipo_norm in ("cpf", "doc_cpf"):
        return consultar_cpf(valor_limpo)
    elif tipo_norm in ("cnpj", "doc_cnpj"):
        return consultar_cnpj(valor_limpo)
    elif tipo_norm == "nome":
        return consultar_nome(valor_limpo)
    else:
        # Fallback inteligente
        if len(digits) in (11, 6) or "***" in valor_limpo:
            return consultar_cpf(valor_limpo)
        elif len(digits) in (14, 8):
            return consultar_cnpj(valor_limpo)
        return consultar_nome(valor_limpo)

def consultar_duckdb(doc_limpo: str, tipo_doc: str):
    """
    Mantido para retrocompatibilidade com código existente.
    """
    if tipo_doc == "CPF":
        res = consultar_cpf(doc_limpo)
        return res.get("risco", "NEGATIVO"), res.get("mensagem", "")
    elif tipo_doc == "CNPJ":
        res = consultar_cnpj(doc_limpo)
        return res.get("risco", "NEGATIVO"), res.get("mensagem", "")
    else:
        res = consultar_nome(doc_limpo)
        return res.get("risco", "NEGATIVO"), res.get("mensagem", "")

def processar_lead(nome: Optional[str] = "", documento: Optional[str] = "", email: Optional[str] = "", valor: Optional[float] = 0.0):
    """
    Processa entrada de lead, validando e consultando conforme os campos informados.
    Permite processamento com documento (CPF/CNPJ), ou somente por Nome, ou combinação.
    """
    doc_str = (documento or "").strip()
    doc_limpo = normalizar(doc_str)
    nome_str = (nome or "").strip()
    email_str = (email or "").strip() or "consulta@sistema.local"
    valor_float = float(valor or 0.0)

    val_cpf, val_cnpj = CPF(), CNPJ()

    # 1. Determina o tipo e valida documento ou nome
    if len(doc_limpo) == 11:
        tipo_doc = "CPF"
        doc_formatado = val_cpf.mask(doc_limpo) if val_cpf.validate(doc_limpo) else doc_str
        resultado = consultar_cpf(doc_formatado)
        status_risco = resultado["risco"]
        detalhes = resultado["mensagem"]
        if not nome_str and resultado.get("peps"):
            nome_str = resultado["peps"][0]["nome_pep"]

    elif len(doc_limpo) == 14:
        tipo_doc = "CNPJ"
        doc_formatado = val_cnpj.mask(doc_limpo) if val_cnpj.validate(doc_limpo) else doc_str
        resultado = consultar_cnpj(doc_formatado)
        status_risco = resultado["risco"]
        detalhes = resultado["mensagem"]
        if not nome_str and resultado.get("empresa"):
            nome_str = resultado["empresa"]["razao_social"]

    elif len(doc_limpo) == 8 and (doc_str.isdigit() or "/" in doc_str or "." in doc_str):
        tipo_doc = "CNPJ"
        doc_formatado = f"{doc_limpo[:8]}"
        resultado = consultar_cnpj(doc_formatado)
        status_risco = resultado["risco"]
        detalhes = resultado["mensagem"]
        if not nome_str and resultado.get("empresa"):
            nome_str = resultado["empresa"]["razao_social"]

    elif nome_str:
        # Se não há documento válido ou preenchido, analisa somente por Nome
        tipo_doc = "NOME"
        doc_formatado = "NÃO INFORMADO"
        resultado = consultar_nome(nome_str)
        status_risco = resultado["risco"]
        detalhes = resultado["mensagem"]

    else:
        return {
            "status": "ERRO",
            "mensagem": "Informe ao menos um parâmetro para análise: Nome, CPF (11 dígitos) ou CNPJ (14 dígitos)."
        }

    nome_final = nome_str if nome_str else f"Consulta {tipo_doc}: {doc_formatado}"

    # 2. Roteamento e Persistência na trilha de auditoria
    destino = EMAIL_DESTINO_COMERCIAL if status_risco == "NEGATIVO" else EMAIL_DESTINO_JURIDICO
    lead_id = salvar_lead(nome_final, tipo_doc, doc_formatado, email_str, valor_float, status_risco, detalhes, destino)

    # 3. Disparo de Notificações
    if status_risco == "NEGATIVO":
        corpo = f"""
        <div style="font-family: Arial, sans-serif; padding: 16px; border-left: 4px solid #10b981;">
            <h2 style="color: #065f46;">Lead Aprovado para Abordagem Comercial</h2>
            <p><strong>ID:</strong> #{lead_id} | <strong>Tipo:</strong> {tipo_doc}</p>
            <p><strong>Nome/Razão Social:</strong> {nome_final}</p>
            <p><strong>Documento:</strong> {doc_formatado}</p>
            <p><strong>E-mail:</strong> {email_str}</p>
            <p><strong>Volume Estimado:</strong> R$ {valor_float:,.2f}</p>
            <p style="color: #10b981;"><strong>Status Compliance:</strong> FICHA LIMPA (Checagem DuckDB)</p>
        </div>
        """
        enviar_email(destino, f"[LEAD APROVADO] {nome_final} - Liberado para Vendas", corpo)
    else:
        corpo = f"""
        <div style="font-family: Arial, sans-serif; padding: 16px; border-left: 4px solid #ef4444;">
            <h2 style="color: #991b1b;">ALERTA REGULATÓRIO: Proposta Retida para Compliance</h2>
            <p><strong>ID:</strong> #{lead_id} | <strong>Tipo:</strong> {tipo_doc}</p>
            <p><strong>Nome/Razão Social:</strong> {nome_final}</p>
            <p><strong>Documento:</strong> {doc_formatado}</p>
            <div style="background: #fee2e2; padding: 10px; border-radius: 4px; margin-top: 10px;">
                <strong>Apontamento Detectado (DuckDB):</strong><br>{detalhes}
            </div>
        </div>
        """
        enviar_email(destino, f"[ALERTA DE RISCO] Lead #{lead_id} Retido: {nome_final}", corpo)

    return {
        "status": "SUCESSO",
        "lead_id": lead_id,
        "tipo_documento": tipo_doc,
        "risco": status_risco,
        "detalhes": detalhes,
        "destino": destino,
        "resultado_detalhado": resultado
    }