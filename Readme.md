# 🛡️ LeadScutum | Motor Analítico de Risco, Compliance e Triagem de Leads

Português

> Esteira automatizada de qualificação cadastral e triagem regulatória de clientes/parceiros com cruzamento em tempo real via **DuckDB** contra bases de PEPs e Quadro de Sócios e Administradores (QSA).

English

> Automated pipeline for client/partner registration qualification and regulatory screening, featuring real-time cross-referencing via **DuckDB** against PEP databases and the Registry of Partners and Administrators (QSA).

---

## 📌 Visão Geral do Projeto

No setor segurador e financeiro, a esteira de onboarding de novos clientes (leads) lida constantemente com um dilema operacional:
1. **Fricção Comercial:** Atraso na qualificação de propostas idôneas por conta de filas manuais de auditoria.
2. **Exposição Regulatória:** Risco severo de avançar contratos com Pessoas Politicamente Expostas (PEPs) ou entidades sancionadas sem parecer prévio de compliance (exigências de órgãos como SUSEP e BACEN).

**A Solução:** Uma esteira ponta a ponta que recebe dados de entrada (CPF ou CNPJ), executa consultas relacionais de alta performance em bases públicas estruturadas em formato colunar (DuckDB) e bifurca a ação:
- **Risco Negativo (Ficha Limpa):** Encaminhamento prioritário à **Área Comercial** para fechamento imediato.
- **Risco Positivo (Match PEP/QSA):** Retenção preventiva e despacho com dossiê analítico para a **Área Jurídica/Compliance**.

## 📌 Project Overview

In the insurance and financial sectors, the onboarding pipeline for new clients (leads) constantly faces an operational dilemma:

1. **Commercial Friction:** Delays in qualifying legitimate proposals due to manual review queues.
2. **Regulatory Exposure:** Severe risk of advancing contracts involving Politically Exposed Persons (PEPs) or sanctioned entities without prior compliance approval (mandated by regulatory bodies such as SUSEP and BACEN).

**The Solution:** An end-to-end pipeline that takes input data (tax ID / CPF or CNPJ), runs high-performance relational queries against public datasets structured in columnar format (DuckDB), and bifurcates the workflow:

* **Low Risk (Clean Record):** Priority routing directly to the **Sales Team** for immediate closing.
* **High Risk (PEP / Corporate Structure Match):** Preventive hold and automatic dispatch with an analytical dossier to the **Legal & Compliance Team**.

---

## 🏗️ Arquitetura da Solução