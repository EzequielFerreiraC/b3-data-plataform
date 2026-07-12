# PRD Funcional - B3 Data Platform

| Campo     | Valor                                        |
| --------- | -------------------------------------------- |
| Produto   | B3 Data Platform (Data Lakehouse Financeiro) |
| Documento | Product Requirements Document (Funcional)    |
| Versao    | 1.0                                          |
| Data      | 2026-07-15                                   |
| Status    | Aprovado para desenvolvimento                |
| Autor     | Ezequiel FC                                  |

---

## 1. Visao Geral

### 1.1 Resumo Executivo

A B3 Data Platform e um data lakehouse financeiro para dados da B3 (Bolsa de
Valores brasileira), construido sobre a Arquitetura Medallion (Bronze, Silver,
Gold e camada de Report). A plataforma ingere, transforma, agrega e analisa dados
diarios de precos (OHLCV) de acoes negociadas na B3, gerando metricas analiticas
e relatorios em PDF de forma automatizada.

### 1.2 Visao do Produto

Oferecer uma base de dados confiavel, versionada e governada de precos historicos
da B3, com metricas analiticas prontas para consumo e relatorios periodicos que
apoiem o acompanhamento de desempenho e risco de uma carteira de acoes.

### 1.3 Problema

O acompanhamento de dados do mercado acionario brasileiro exige coletar,
padronizar e validar precos de multiplas fontes, calcular metricas de risco e
retorno e consolidar tudo em relatorios. Fazer isso manualmente e propenso a
erros, dificil de reproduzir e nao escala.

### 1.4 Solucao

Um pipeline automatizado ponta a ponta que:

- Extrai dados diarios de precos de fontes externas (Yahoo Finance e BRAPI).
- Aplica limpeza, deduplicacao e validacao de qualidade.
- Calcula metricas analiticas (retornos, volatilidade, retorno acumulado).
- Gera relatorios em PDF com graficos.
- Orquestra todo o fluxo com agendamento diario.

---

## 2. Objetivos e Metas

### 2.1 Objetivos de Produto

1. Automatizar a ingestao diaria de precos de acoes da B3.
2. Garantir qualidade e consistencia dos dados por meio de validacoes.
3. Disponibilizar metricas analiticas prontas para consumo.
4. Produzir relatorios periodicos de desempenho e risco.
5. Assegurar reprodutibilidade e rastreabilidade dos dados.

### 2.2 Metricas de Sucesso (KPIs)

| Metrica                                 | Meta                             |
| --------------------------------------- | -------------------------------- |
| Tickers acompanhados por padrao         | 12 acoes da B3                   |
| Cobertura historica inicial             | 365 dias                         |
| Execucao do pipeline                    | Diaria (dias uteis)              |
| Camadas da arquitetura Medallion        | 4 (Bronze, Silver, Gold, Report) |
| Checagens de qualidade na camada Silver | >= 4                             |
| Relatorio PDF gerado por execucao       | 1                                |

### 2.3 Nao Objetivos (Fora de Escopo)

- Nao e uma plataforma de execucao de ordens (trading).
- Nao fornece recomendacoes de investimento.
- Nao processa dados intradiarios (foco em dados diarios de fechamento).
- Nao cobre outras bolsas alem da B3 no escopo inicial.

---

## 3. Personas

| Persona                       | Descricao                    | Necessidade principal                       |
| ----------------------------- | ---------------------------- | ------------------------------------------- |
| Analista de dados financeiros | Estuda desempenho de acoes   | Metricas confiaveis e relatorios prontos    |
| Engenheiro(a) de dados        | Mantem e evolui os pipelines | Pipelines modulares e observaveis           |
| Gestor(a) de carteira         | Acompanha risco e retorno    | Resumo de portfolio e relatorios periodicos |
| Cientista de dados            | Explora e modela dados       | Acesso a dados limpos e camadas analiticas  |

---

## 4. Requisitos Funcionais

### 4.1 Ingestao (Bronze)

**RF-01** O sistema deve extrair precos diarios OHLCV (abertura, maxima, minima,
fechamento, fechamento ajustado e volume) de uma lista configuravel de tickers.

**RF-02** O sistema deve suportar Yahoo Finance como fonte primaria (tickers no
formato `.SA`).

**RF-03** O sistema deve suportar BRAPI como fonte alternativa (tickers sem
sufixo `.SA`, autenticacao via token opcional).

**RF-04** O sistema deve armazenar os dados brutos de forma imutavel, adicionando
metadados de origem (`source`) e timestamp de ingestao (`ingested_at`).

**RF-05** O sistema deve tolerar falhas por ticker, registrando o erro e
prosseguindo com os demais.

### 4.2 Transformacao e Qualidade (Silver)

**RF-06** O sistema deve padronizar tipos, normalizar tickers e renomear colunas.

**RF-07** O sistema deve remover registros com valores nulos em campos-chave
(ticker, data, preco de fechamento, volume).

**RF-08** O sistema deve remover registros com precos invalidos (zero ou
negativos).

**RF-09** O sistema deve deduplicar registros por (ticker, data), mantendo o de
maior fechamento ajustado.

**RF-10** O sistema deve calcular o retorno diario por ticker.

**RF-11** O sistema deve executar checagens de qualidade que falham rapidamente
em caso de: nulos em campos-chave, precos nao positivos, duplicidade de
(ticker, data) e datas futuras.

### 4.3 Agregacao Analitica (Gold)

**RF-12** O sistema deve gerar a tabela `daily_metrics` com fechamento, retorno
diario, media movel de volume de 20 dias, volatilidade anualizada de 20 dias e
retorno acumulado por ticker.

**RF-13** O sistema deve gerar a tabela `portfolio_summary` com um registro por
ticker, incluindo retorno total, volume medio, volatilidade media, maxima e
minima do periodo.

**RF-14** O sistema deve gerar a tabela `monthly_returns` com agregacoes mensais
no estilo OHLC e retorno do mes.

### 4.4 Relatorio (Report)

**RF-15** O sistema deve gerar um relatorio em PDF por execucao contendo graficos
de retorno acumulado, volatilidade, risco versus retorno e heatmap de retornos
mensais.

**RF-16** O sistema deve nomear e armazenar o relatorio com carimbo de data/hora.

### 4.5 Orquestracao

**RF-17** O sistema deve orquestrar as camadas em sequencia
(Bronze -> Silver -> Gold -> Report) com agendamento em dias uteis.

**RF-18** Cada camada deve depender da conclusao bem-sucedida da camada anterior.

**RF-19** O sistema deve aplicar politicas de retry por camada em caso de falha.

---

## 5. Fluxos de Uso

### 5.1 Fluxo Diario Automatizado

1. Ao final do pregao, o DAG Bronze extrai precos do dia e grava dados brutos.
2. O DAG Silver aguarda a conclusao do Bronze, limpa, valida e calcula retornos.
3. O DAG Gold aguarda o Silver e gera as tabelas analiticas.
4. O DAG Report aguarda o Gold e gera o relatorio PDF.
5. O relatorio fica disponivel na pasta de saidas.

### 5.2 Fluxo de Exploracao Interativa

1. Analista abre o JupyterLab.
2. Le as camadas Silver ou Gold.
3. Explora metricas e gera visualizacoes ad hoc.

---

## 6. Escopo de Entrega

### 6.1 Dentro do Escopo (MVP)

- Ingestao diaria de 12 tickers da B3.
- Camadas Bronze, Silver, Gold e Report.
- Validacoes de qualidade na camada Silver.
- Relatorio PDF automatizado.
- Orquestracao com Airflow e armazenamento em MinIO.

### 6.2 Fora do Escopo (MVP)

- Dados intradiarios e streaming em tempo real.
- Dashboards interativos web.
- Alertas e notificacoes automatizadas.
- Modelos preditivos de precos.

---

## 7. Premissas, Restricoes e Dependencias

### 7.1 Premissas

- As fontes externas (Yahoo Finance, BRAPI) estao disponiveis e retornam dados
  consistentes.
- O ambiente executa via Docker Compose.

### 7.2 Restricoes

- Foco em dados diarios de fechamento.
- Dependencia de disponibilidade e limites das APIs externas.

### 7.3 Dependencias

- Fontes de dados: Yahoo Finance (yfinance) e BRAPI.
- Infraestrutura: MinIO, PostgreSQL, Airflow e JupyterLab (via Docker Compose).

---

## 8. Roadmap (Alto Nivel)

| Fase   | Entrega                                                   |
| ------ | --------------------------------------------------------- |
| Fase 1 | Pipeline Medallion completo com relatorio PDF (concluido) |
| Fase 2 | Expansao de tickers e indicadores adicionais              |
| Fase 3 | Dashboards interativos e distribuicao de relatorios       |
| Fase 4 | Alertas de risco e deteccao de anomalias                  |

---

## 9. Criterios de Aceite

- O pipeline executa ponta a ponta em dias uteis sem intervencao manual.
- As checagens de qualidade impedem a promocao de dados invalidos para Silver.
- As tabelas Gold refletem corretamente as metricas definidas.
- O relatorio PDF e gerado com os quatro graficos especificados.
