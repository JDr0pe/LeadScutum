# 🛡️ LeadScutum | Motor Analítico de Risco, Compliance e Consulta de PEPs
### Regulatory Risk, Compliance Analytics & PEP Screening Engine

[🇧🇷 Português](#-versão-em-português) • [🇺🇸 English](#-english-version)

---

## 🇧🇷 Versão em Português

> Esteira automatizada de qualificação cadastral e triagem regulatória de clientes/parceiros com cruzamento em tempo real via **DuckDB** contra bases de PEPs (CGU) e Quadro de Sócios e Administradores (QSA - Receita Federal).

### 📌 Visão Geral do Projeto

No setor financeiro e segurador, a verificação de conformidade regulatória (compliance) exige respostas rápidas e precisas:
1. **Fricção Comercial:** Atraso na qualificação de propostas por conta de filas manuais de auditoria.
2. **Exposição Regulatória:** Risco severo de avançar contratos com Pessoas Politicamente Expostas (PEPs) ou entidades sancionadas sem parecer prévio de compliance (exigências de órgãos como SUSEP, CVM e BACEN).

**A Solução:** Uma esteira ponta a ponta e motor de busca analítico de alta performance em formato colunar (DuckDB):
- **Consulta Direta Rápida:** Possibilidade de consultar **somente por Nome**, **somente por CNPJ** ou **somente por CPF**, retornando imediatamente o parecer de risco e o dossiê detalhado.
- **Roteamento Inteligente de Leads:**
  - **Ficha Limpa (Risco Negativo):** Despacho prioritário à Área Comercial para fechamento.
  - **Match PEP / QSA (Risco Positivo):** Retenção preventiva e envio automático à Área Jurídica/Compliance com dossiê analítico.
- **Trilha de Auditoria:** Persistência em SQLite para governança e relatórios regulatórios.

---

### 🚀 Como Executar

#### 1. Pré-requisitos
- Python 3.10+
- Virtualenv com as dependências do `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

#### 2. Configurar o arquivo `.env`
Copie o modelo `.env.example` para `.env` e insira seu token e e-mails de destino:
```bash
cp .env.example .env
```
Variáveis disponíveis no `.env`:
- `MAILTRAP_API_TOKEN`: seu token da API do Mailtrap.
- `MAILTRAP_SENDER_EMAIL`: e-mail de envio (padrão: `hello@demomailtrap.co`).
- `EMAIL_DESTINO_COMERCIAL`: e-mail para receber leads aprovados (ficha limpa).
- `EMAIL_DESTINO_JURIDICO`: e-mail para receber leads retidos (alerta PEP).

#### 3. Iniciar a Aplicação
```bash
uvicorn main:app --reload --port 8000
```
Acesse no navegador: [http://localhost:8000](http://localhost:8000)

---

### 🔍 Funcionalidades de Consulta

#### 1. Consulta Somente por Nome
- Permite pesquisar pessoas físicas na base de PEPs da CGU ou razões sociais de empresas com sócios PEP.
- Suporta busca case-insensitive e acentuação flexível via `strip_accents`.
- Exemplo: `"Celso Fioreze"`, `"Lula"`.

#### 2. Consulta Somente por CPF
- Permite pesquisar por CPF completo (11 dígitos), mascarado (`***.XXX.XXX-**`) ou dígitos intermediários.
- Cruza com a base de PEPs e busca instantaneamente vínculos societários (empresas onde o PEP é sócio).

#### 3. Consulta Somente por CNPJ
- Permite pesquisar por CNPJ completo (14 dígitos) ou CNPJ básico (8 dígitos).
- Obtém dados cadastrais da empresa (`empresas`), lista os sócios (`socios`) e identifica sócios PEP no QSA (`vw_pep_socios_empresas`).

---

### 📡 Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/consultar` | Consulta direta por Nome, CPF ou CNPJ (`{"tipo": "nome"|"cpf"|"cnpj"|"auto", "valor": "..."}`) |
| `GET` | `/api/consultar` | Consulta via parâmetros de URL (`?q=...`, `?cpf=...`, `?cnpj=...`, `?nome=...`) |
| `POST` | `/api/processar-lead` | Entrada na esteira de triagem e persistência de lead com envio de notificação |
| `GET` | `/api/leads` | Histórico dos últimos leads processados na auditoria |

---

### 🏗️ Estrutura do Projeto

```
consulta_peps/
├── dados.duckdb           # Banco colunar DuckDB com tabelas pep, empresas, socios e views
├── compliance_leads.db    # Banco SQLite de trilha de auditoria
├── engine.py              # Motor de checagem analítica e consultas DuckDB
├── database.py            # Inicialização e persistência de auditoria SQLite
├── mailer.py              # Disparo de alertas regulatórios
├── main.py                # Servidor FastAPI e rotas REST
├── static/
│   └── index.html         # Frontend moderno (Tailwind CSS + Phosphor Icons)
├── .env.example           # Modelo de variáveis de ambiente (Mailtrap e e-mails)
└── requirements.txt       # Dependências Python
```

---

## 🇺🇸 English Version

> Automated pipeline for client/partner registration qualification and regulatory screening, featuring real-time cross-referencing via **DuckDB** against PEP databases (CGU) and the Registry of Partners and Administrators (QSA - Brazilian Federal Revenue).

### 📌 Project Overview

In the insurance and financial sectors, the onboarding pipeline for new clients (leads) constantly faces an operational dilemma:

1. **Commercial Friction:** Delays in qualifying legitimate proposals due to manual review queues.
2. **Regulatory Exposure:** Severe risk of advancing contracts involving Politically Exposed Persons (PEPs) or sanctioned entities without prior compliance approval (mandated by regulatory bodies such as SUSEP, CVM, and BACEN).

**The Solution:** An end-to-end pipeline and high-performance columnar analytical search engine (DuckDB):
- **Fast Direct Lookup:** Ability to query **solely by Name**, **solely by CNPJ**, or **solely by CPF**, instantly returning the compliance risk assessment and detailed dossier in milliseconds (< 50ms).
- **Intelligent Lead Routing:**
  - **Low Risk (Clean Record):** Priority routing directly to the **Sales Team** for immediate closing.
  - **High Risk (PEP / Corporate Structure Match):** Preventive hold and automatic dispatch with an analytical dossier to the **Legal & Compliance Team**.
- **Immutable Audit Trail:** SQLite persistence for compliance governance and regulatory reporting.

---

### 🚀 Getting Started

#### 1. Prerequisites
- Python 3.10+
- Virtual environment with dependencies from `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

#### 2. Configure the `.env` File
Copy `.env.example` to `.env` and fill in your token and alert recipient emails:
```bash
cp .env.example .env
```
Environment variables:
- `MAILTRAP_API_TOKEN`: your Mailtrap API token.
- `MAILTRAP_SENDER_EMAIL`: sender address (default: `hello@demomailtrap.co`).
- `EMAIL_DESTINO_COMERCIAL`: recipient email for approved clean leads.
- `EMAIL_DESTINO_JURIDICO`: recipient email for retained high-risk leads.

#### 3. Run the Application
```bash
uvicorn main:app --reload --port 8000
```
Open in your browser: [http://localhost:8000](http://localhost:8000)

---

### 🔍 Screening & Query Capabilities

#### 1. Query Solely by Name
- Search for individuals in the CGU PEP database or company corporate names with PEP partners.
- Supports case-insensitive and accent-insensitive matching via DuckDB `strip_accents`.
- Examples: `"Celso Fioreze"`, `"Lula"`.

#### 2. Query Solely by CPF
- Search by full CPF (11 digits), masked CPF (`***.XXX.XXX-**`), or the 6 middle digits.
- Cross-references PEP records and instantly retrieves connected corporate ownerships where the PEP is a partner.

#### 3. Query Solely by CNPJ
- Search by full CNPJ (14 digits) or basic CNPJ (first 8 digits).
- Retrieves company registration data (`empresas`), complete partner roster (`socios`), and flags any PEP partners in the corporate structure (`vw_pep_socios_empresas`).

---

### 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/consultar` | Direct query by Name, CPF, or CNPJ (`{"tipo": "nome"|"cpf"|"cnpj"|"auto", "valor": "..."}`) |
| `GET` | `/api/consultar` | Direct query via URL parameters (`?q=...`, `?cpf=...`, `?cnpj=...`, `?nome=...`) |
| `POST` | `/api/processar-lead` | Lead screening pipeline entry, notification dispatch, and audit persistence |
| `GET` | `/api/leads` | Historical list of processed audit leads |

---

### 🏗️ Project Structure

```
consulta_peps/
├── dados.duckdb           # Columnar DuckDB database with pep, empresas, socios tables & views
├── compliance_leads.db    # SQLite database for regulatory audit trails
├── engine.py              # Analytical engine and DuckDB query execution
├── database.py            # SQLite audit trail initialization and persistence
├── mailer.py              # Automated regulatory alert dispatcher
├── main.py                # FastAPI server and REST endpoints
├── static/
│   └── index.html         # Modern web interface (Tailwind CSS + Phosphor Icons)
├── .env.example           # Environment variables template (Mailtrap & emails)
└── requirements.txt       # Python package dependencies
```