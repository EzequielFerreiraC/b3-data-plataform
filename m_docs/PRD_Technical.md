# PRD Tecnico - B3 Data Platform

| Campo     | Valor                                        |
| --------- | -------------------------------------------- |
| Produto   | B3 Data Platform (Data Lakehouse Financeiro) |
| Documento | Product Requirements Document (Tecnico)      |
| Versao    | 1.0                                          |
| Data      | 2026-07-15                                   |
| Status    | Aprovado para desenvolvimento                |
| Autor     | Ezequiel FC                                  |

---

## 1. Contexto Tecnico

A B3 Data Platform implementa a Arquitetura Medallion (Bronze, Silver, Gold e
Report) para dados financeiros da B3. O sistema e composto por modulos Python
para ingestao, processamento e relatorios, orquestrados por Apache Airflow, com
armazenamento em object storage compativel com S3 (MinIO). O processamento usa
Polars para transformacoes rapidas e PySpark/Delta Lake para processamento
distribuido.

---

## 2. Arquitetura

### 2.1 Arquitetura Medallion

```
Fontes externas (Yahoo Finance, BRAPI)
        |
        v
+------------------+   Dados brutos imutaveis (OHLCV + source + ingested_at)
|  a_bronze        |   Particionado por trade_date (Parquet, snappy)
+------------------+
        |
        v
+------------------+   Limpeza, deduplicacao, validacao, retorno diario
|  b_silver        |   DecimalType(18,4) para precos; quality checks fail-fast
+------------------+
        |
        v
+------------------+   Tabelas analiticas:
|  c_gold          |   daily_metrics | portfolio_summary | monthly_returns
+------------------+
        |
        v
+------------------+   Relatorio PDF (FPDF2 + Matplotlib/Seaborn)
|  d_report        |   n_reports/report_YYMMDD_HHMM.pdf
+------------------+
```

### 2.2 Camadas de Infraestrutura (Docker Compose)

| Servico    | Imagem                   | Porta                 | Funcao                             |
| ---------- | ------------------------ | --------------------- | ---------------------------------- |
| MinIO      | minio/minio:latest       | 9000 (API), 9001 (UI) | Object storage compativel com S3   |
| PostgreSQL | postgres:15-alpine       | interna               | Banco de metadados do Airflow      |
| Airflow    | apache/airflow:2.9.1     | 8080                  | Orquestracao e agendamento de DAGs |
| JupyterLab | jupyter/pyspark-notebook | 8888                  | Exploracao interativa de dados     |

### 2.3 Estrutura de Modulos

| Pasta           | Responsabilidade                                     |
| --------------- | ---------------------------------------------------- |
| `a_configs/`    | Settings, config MinIO/S3, config Spark, logger JSON |
| `b_models/`     | Schemas Pydantic e schemas Spark explicitos          |
| `c_ingestion/`  | Adaptadores de fonte (Yahoo Finance, BRAPI)          |
| `d_processing/` | Logica das camadas Bronze, Silver, Gold e Report     |
| `e_validation/` | Checagens de qualidade de dados                      |
| `f_pipelines/`  | Orquestracao por camada (extract/transform/load)     |
| `g_storage/`    | Abstracoes de armazenamento                          |
| `h_dags/`       | DAGs do Airflow                                      |
| `i_notebooks/`  | Notebooks de exploracao                              |
| `j_data/`       | Dados locais por camada                              |
| `k_logs/`       | Logs                                                 |
| `l_tests/`      | Testes                                               |
| `n_reports/`    | Relatorios gerados (PDF)                             |

---

## 3. Stack Tecnologica

| Categoria     | Tecnologias                                                                         |
| ------------- | ----------------------------------------------------------------------------------- |
| Processamento | Polars >= 0.20, PySpark 3.5.1, Delta Lake 3.1.0, Pandas 2.2, NumPy 1.26, PyArrow 14 |
| Ingestao      | yfinance >= 0.2.36, requests >= 2.31                                                |
| Armazenamento | boto3 >= 1.34, s3fs >= 2024.2 (MinIO/S3)                                            |
| Orquestracao  | Apache Airflow >= 2.9                                                               |
| Validacao     | Pydantic >= 2.5, Great Expectations >= 0.18                                         |
| Relatorios    | fpdf2 >= 2.7, Plotly >= 5.18, Matplotlib >= 3.8, Seaborn >= 0.13                    |

---

## 4. Modelo de Dados

### 4.1 Modelos Pydantic (Validacao por Registro)

```python
class RawTrade(BaseModel):        # Bronze
    ticker: str
    trade_date: date
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    adj_close: Optional[Decimal] = None
    volume: Optional[int] = None
    source: str = "yahoo_finance"

class CleanTrade(BaseModel):      # Silver (tipos resolvidos, sem nulos em chave)
    ticker: str
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    adj_close: Decimal
    volume: int
    daily_return: Optional[Decimal] = None
```

### 4.2 Schemas Spark (Explicitos, nunca inferidos)

| Schema            | Campos-chave                                                                       | Tipos                                      |
| ----------------- | ---------------------------------------------------------------------------------- | ------------------------------------------ |
| BRONZE_SCHEMA     | ticker, trade_date, OHLCV, source, ingested_at                                     | String, Date, Double/Long, Timestamp       |
| SILVER_SCHEMA     | precos, volume, daily_return, processed_at                                         | DecimalType(18,4), Long, Double, Timestamp |
| GOLD_DAILY_SCHEMA | close_price, daily_return, avg_volume_20d, volatility_20d, cum_return, year, month | Decimal, Double, Integer                   |

---

## 5. Especificacao das Camadas de Processamento

### 5.1 Bronze (`d_processing/a_bronze/`)

- Imutabilidade: reexecucao sobrescreve a particao inteira.
- Sem transformacao: valores intocados da fonte.
- Metadados adicionados: `source`, `ingested_at` (UTC).
- Particionamento: por `trade_date` (formato `YYMMDD_HHMM`).
- Caminho: `j_data/a_bronze/<source>/trade_date_YYMMDD_HHMM/data.parquet`.
- Compressao: snappy.

### 5.2 Silver (`d_processing/b_silver/`) - Pipeline de 6 etapas

1. `cast_types`: precos para Float64, volume para Int64, ticker normalizado,
   renomeacao de colunas.
2. `remove_nulls`: descarta nulos em ticker, trade_date, close_price, volume.
3. `remove_invalid_prices`: filtra precos <= 0.
4. `deduplicate`: 1 registro por (ticker, trade_date), maior adj_close vence.
5. `calculate_daily_return`: `(close_price / prev_close) - 1` por ticker.
6. `add_metadata` + `select_silver_columns`: adiciona `processed_at` e ordena.

### 5.3 Gold (`d_processing/c_gold/`) - 3 Tabelas Analiticas

| Tabela            | Grao           | Colunas principais                                                                                          |
| ----------------- | -------------- | ----------------------------------------------------------------------------------------------------------- |
| daily_metrics     | ticker-data    | close_price, daily_return, avg_volume_20d, volatility_20d (anualizada x sqrt(252)), cum_return, year, month |
| portfolio_summary | ticker         | first_date, last_date, total_return, avg_daily_volume, avg_volatility, period_high, period_low              |
| monthly_returns   | ticker-ano-mes | month_open, month_close, month_high, month_low, month_volume, avg_daily_return, month_return                |

### 5.4 Report (`d_processing/d_report/`)

- Ferramentas: FPDF2 + Matplotlib/Seaborn.
- Graficos: retorno acumulado (top 5), volatilidade 20d (top 5), risco versus
  retorno (scatter), heatmap de retornos mensais.
- Saida: `n_reports/report_YYMMDD_HHMM.pdf` (DPI 150).

---

## 6. Orquestracao (Airflow DAGs)

| DAG                    | Agendamento (UTC) | Dependencia                  | Retries         |
| ---------------------- | ----------------- | ---------------------------- | --------------- |
| a_b3_bronze_ingestion  | `0 22 * * 1-5`    | -                            | 3 x 5 min       |
| b_b3_silver_etl        | `30 22 * * 1-5`   | ExternalTaskSensor no Bronze | 2 x 10 min      |
| c_b3_gold_aggregation  | `0 23 * * 1-5`    | ExternalTaskSensor no Silver | 2 x 10 min      |
| d_b3_report_generation | `30 23 * * 1-5`   | ExternalTaskSensor no Gold   | conforme padrao |

- Sensores em modo `reschedule`, timeout de 3600s.
- O DAG de Report publica `report_path` via XCom em caso de sucesso.

### 6.1 Padrao de Pipeline

Cada pipeline segue o contrato `extract() -> transform() -> load() -> run()`:

- BronzePipeline: `extract` (fetch), `load` (write_bronze).
- SilverPipeline: `extract` (read_bronze), `transform` (+ quality checks),
  `load` (write_silver).
- GoldPipeline: `extract` (read_silver), `transform` (3 tabelas), `load`.
- ReportPipeline: `extract` (read_gold), `generate` (PDF).

---

## 7. Configuracao

### 7.1 Parametros Principais (`a_configs/settings.py`)

```python
DATA_PATH_BRONZE = ROOT_DIR / "j_data/a_bronze"
DATA_PATH_SILVER = ROOT_DIR / "j_data/b_silver"
DATA_PATH_GOLD   = ROOT_DIR / "j_data/c_gold"

MINIO_ENDPOINT       = "http://localhost:9000"
MINIO_BUCKET_BRONZE  = "b3-bronze"
MINIO_BUCKET_SILVER  = "b3-silver"
MINIO_BUCKET_GOLD    = "b3-gold"

SPARK_APP_NAME = "b3-data-platform"
SPARK_MASTER   = "local[*]"

DEFAULT_TICKERS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
    "WEGE3.SA", "RENT3.SA", "MGLU3.SA", "BPAC11.SA", "LREN3.SA",
    "BBAS3.SA", "RADL3.SA",
]
```

### 7.2 Spark (`a_configs/spark_config.py`)

- Extensoes Delta Lake 3.1.0.
- Adaptive Query Execution (AQE) habilitado.
- Parquet date rebase mode: CORRECTED.
- Hadoop home configurado para compatibilidade Windows/WSL.

### 7.3 Logging (`a_configs/logger.py`)

- Logs estruturados em JSON: timestamp (ISO 8601 UTC), nivel, logger, mensagem,
  modulo, funcao, linha e campos extras (rows, date, ticker, error).

---

## 8. Requisitos Nao Funcionais

| ID     | Requisito            | Criterio                                               |
| ------ | -------------------- | ------------------------------------------------------ |
| RNF-01 | Reprodutibilidade    | Bronze imutavel; reexecucao sobrescreve particao       |
| RNF-02 | Qualidade de dados   | Quality checks fail-fast antes de promover para Silver |
| RNF-03 | Observabilidade      | Logs estruturados em JSON com contexto por evento      |
| RNF-04 | Escalabilidade       | Suporte a PySpark/Delta para volumes crescentes        |
| RNF-05 | Resiliencia          | Retries por DAG e tolerancia a falha por ticker        |
| RNF-06 | Governanca de schema | Schemas Spark explicitos, nunca inferidos              |
| RNF-07 | Portabilidade        | Execucao via Docker Compose                            |

---

## 9. Seguranca

- **Credenciais externas**: token da BRAPI via variavel de ambiente
  (`B3_API_TOKEN`), nunca hardcoded em codigo de dominio.
- **Segredos de infraestrutura**: credenciais padrao do MinIO devem ser
  substituidas em ambientes nao locais (variaveis de ambiente/secret manager).
- **Isolamento**: servicos executam em containers segregados via Docker Compose.
- **Validacao de entrada**: dados externos passam por schemas e quality checks
  antes de qualquer promocao de camada.
- **Least privilege**: buckets e credenciais devem ser escopados por ambiente.

---

## 10. Testes e Validacao

| Tipo                       | Descricao                                               |
| -------------------------- | ------------------------------------------------------- |
| Quality checks (Silver)    | Nulos, precos nao positivos, duplicidade, datas futuras |
| Testes de transformacao    | Validar cada etapa do pipeline Silver                   |
| Testes de agregacao (Gold) | Conferir metricas (volatilidade, cum_return, mensais)   |
| Testes de ingestao         | Simular falhas por ticker e diferencas de versao da API |
| Testes de orquestracao     | Verificar dependencias e sensores entre DAGs            |

---

## 11. Setup e Execucao

- `setup.sh` / `setup.bat`: preparam o ambiente (dependencias e estrutura).
- `docker-compose.yml`: sobe MinIO, PostgreSQL, Airflow e JupyterLab.
- Acesso: Airflow (8080), MinIO Console (9001), JupyterLab (8888).

---

## 12. Riscos Tecnicos e Mitigacoes

| Risco                            | Impacto                   | Mitigacao                                                 |
| -------------------------------- | ------------------------- | --------------------------------------------------------- |
| Instabilidade das APIs externas  | Falha de ingestao         | Retries, tolerancia por ticker, fonte alternativa (BRAPI) |
| Segfault do curl_cffi em WSL     | Falha no yfinance         | Uso de `requests` como fallback                           |
| Diferencas de versao do yfinance | Colunas divergentes       | Normalizacao de colunas (Date/Datetime)                   |
| Credenciais padrao do MinIO      | Exposicao em nao local    | Substituicao obrigatoria por variaveis de ambiente        |
| Crescimento de volume            | Degradacao de performance | PySpark/Delta e particionamento por data                  |
