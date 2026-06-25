# Roteiro de Apresentação Técnica — B3 Data Platform (5 min)

> Fala literal, com indicação de quais arquivos abrir e quais gráficos mostrar.
> Tempo-alvo: 5 minutos · ritmo confortável: ~140 palavras/minuto.

---

## [0:00 – 0:30] Abertura e contexto

**[Tela: README.md aberto]**

> "Bom dia, pessoal. Vou apresentar o **B3 Data Platform**, que é uma plataforma de dados financeiros construída em cima da arquitetura *Medallion* — Bronze, Silver e Gold — para tratar cotações diárias das principais ações da bolsa brasileira, a B3.
>
> A ideia central do projeto é simular um *data lakehouse* local, ponta a ponta: desde a ingestão dos dados brutos via Yahoo Finance, passando pela limpeza e enriquecimento, até chegar em tabelas analíticas prontas para consumo, com visualizações em Jupyter."

---

## [0:30 – 1:10] Stack e arquitetura

**[Continuar no README.md, rolar até a tabela "Stack"]**

> "Do ponto de vista de stack, eu trabalhei com **Polars** como motor principal de transformação, por ser extremamente performático em volumes médios, e mantive **PySpark** disponível para o cenário de grande volume — inclusive com *schemas* declarados explicitamente, sem `inferSchema`.
>
> O armazenamento usa **MinIO**, que é um *object storage* compatível com S3, rodando localmente via **Docker Compose**. Os dados são persistidos em **Parquet** particionado por data de pregão. Para exploração e visualização, eu uso **JupyterLab** com **Plotly** e **Seaborn**. E toda a configuração — caminhos, credenciais, *tickers* padrão — está centralizada em `a_configs/settings.py`, ou seja, nada de `os.environ` espalhado pelo código.
>
> Repare também que as pastas do projeto seguem um padrão de prefixo por letra — `a_configs`, `b_models`, `c_ingestion`, e assim por diante — para deixar a ordem de leitura natural no explorador de arquivos."

---

## [1:10 – 1:50] Camada Bronze — ingestão crua

**[Abrir `c_ingestion/yahoo_finance.py`]**

> "A camada Bronze começa aqui, no `yahoo_finance.py`. Esse módulo faz o *download* dos *tickers* — PETR4, VALE3, ITUB4, e por aí vai — usando a biblioteca `yfinance`, e devolve um DataFrame Polars já normalizado: nomes em *snake_case*, datas tipadas, *ticker* como coluna explícita."

**[Abrir `d_processing/bronze/ingest.py`]**

> "E aqui, no `ingest.py`, está o gravador da Bronze. O contrato dessa camada é simples: **imutabilidade**. Eu só anexo metadados — `source` e `ingested_at` — e gravo o dado exatamente como veio, particionado por `trade_date`. Nada é transformado nessa etapa. Isso garante rastreabilidade: se algo der errado nas camadas seguintes, eu sempre consigo reprocessar a partir do dado bruto original."

---

## [1:50 – 2:40] Camada Silver — limpeza e qualidade

**[Abrir `d_processing/silver/transform.py`]**

> "Na Silver é onde a coisa fica interessante. Eu montei o pipeline como uma sequência de funções puras, encadeadas com `.pipe()`, o que deixa o fluxo bem legível: *cast* de tipos, remoção de nulos, remoção de preços inválidos — qualquer coisa menor ou igual a zero —, *deduplicação* por `ticker` mais `trade_date`, cálculo do **retorno diário** com função de janela por *ticker*, e por fim o *timestamp* de processamento."

**[Abrir `e_validation/quality_checks.py`]**

> "E acoplado a isso, em `quality_checks.py`, eu tenho um conjunto de checagens *fail-fast*: garante que não existe nulo nas colunas-chave, que não há preço negativo, que não há duplicata na chave de negócio, e que nenhuma data está no futuro. Se qualquer uma falhar, o *pipeline* aborta com `AssertionError`. Isso evita que dado sujo contamine a Gold."

---

## [2:40 – 3:30] Camada Gold — agregações analíticas

**[Abrir `d_processing/gold/aggregate.py`]**

> "A camada Gold é o produto final, voltado para análise. Eu gero três tabelas:
>
> Primeiro, `daily_metrics` — que é o grão diário enriquecido com **volume médio de 20 dias**, **volatilidade de 20 dias anualizada** multiplicando por raiz de 252, e o **retorno acumulado composto** por *ticker*.
>
> Segundo, `portfolio_summary`, com uma linha por ativo: retorno total no período, volume médio, volatilidade média, máximas e mínimas.
>
> E terceiro, `monthly_returns`, que agrega por *ticker*, ano e mês — abertura no primeiro dia, fechamento no último — e calcula o retorno mensal. Tudo gravado em Parquet particionado por ano e mês."

---

## [3:30 – 4:40] Notebook de análise e gráficos

**[Abrir `i_notebooks/03_gold_analytics.ipynb` e ir rolando célula a célula]**

> "Agora vamos ver o resultado disso tudo no notebook `03_gold_analytics`.

**[Mostrar gráfico 1 — Cumulative Returns]**

> "Esse primeiro gráfico é o **retorno acumulado** de todos os *tickers* no período. Cada linha é uma ação. Aqui dá pra ver claramente quem foram os vencedores e os perdedores do período — algumas ações entregaram retornos positivos consistentes, enquanto outras ficaram lateralizadas ou negativas.

**[Mostrar gráfico 2 — 20-Day Annualised Volatility]**

> "Esse segundo gráfico é a **volatilidade anualizada de 20 dias**. Repare nos picos: eles coincidem com janelas de estresse de mercado, e mostram que mesmo ativos *blue chip* têm períodos de oscilação muito acima da média.

**[Mostrar gráfico 3 — Risk vs Return scatter]**

> "Esse aqui é o **scatter de risco contra retorno** — cada ponto é um *ticker*. É a leitura clássica de portfólio: quem está no canto superior esquerdo entregou retorno alto com volatilidade baixa, ou seja, melhor relação risco-retorno; quem está embaixo à direita assumiu risco e não foi remunerado por isso.

**[Mostrar gráfico 4 — Monthly Returns Heatmap]**

> "E por último, o **heatmap de retornos mensais**: ativos nas linhas, meses nas colunas. Verde é mês positivo, vermelho é negativo. Esse é o gráfico que mais entrega valor visual rápido — dá pra identificar meses em que o mercado inteiro caiu junto, e ativos com comportamento descorrelacionado do resto."

---

## [4:40 – 5:00] Conclusão

**[Voltar para o notebook ou para o README]**

> "Concluindo: a plataforma cumpriu o objetivo de transformar dado bruto, sem nenhum tratamento, em **informação acionável** para análise de portfólio.
>
> Os gráficos deixaram claro três coisas:
> primeiro, que existe **dispersão significativa de retorno** entre ativos do mesmo índice, o que reforça o valor da diversificação;
> segundo, que **risco e retorno não andam juntos automaticamente** — alguns ativos foram bem mais voláteis sem entregar retorno proporcional;
> e terceiro, que existem **janelas mensais de estresse sincronizado**, visíveis no heatmap, que justificam a importância de monitorar volatilidade em janela móvel.
>
> A arquitetura em camadas garantiu que cada uma dessas conclusões fosse extraída a partir de um dado **rastreável, validado e reprocessável**. Obrigado."

---

### Notas práticas

- **Abra o VS Code com a árvore expandida** mostrando: `a_configs/`, `c_ingestion/`, `d_processing/`, `e_validation/`, `i_notebooks/`.
- **Execute o notebook 03 antes** da apresentação para que os gráficos já estejam renderizados.
- **Ordem dos arquivos para abrir**, em sequência:
  1. `README.md`
  2. `c_ingestion/yahoo_finance.py`
  3. `d_processing/bronze/ingest.py`
  4. `d_processing/silver/transform.py`
  5. `e_validation/quality_checks.py`
  6. `d_processing/gold/aggregate.py`
  7. `i_notebooks/03_gold_analytics.ipynb`
