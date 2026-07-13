# Z_Infra — Docker Infrastructure

Esta pasta contém todos os arquivos relacionados à infraestrutura Docker do projeto B3 Data Platform.

## Arquivos

### docker-compose.yml

Orquestra todos os serviços necessários para a plataforma:

- **MinIO**: Object storage (S3-compatible) para dados Bronze/Silver/Gold
  - API: http://localhost:9000
  - Console: http://localhost:9001 (minioadmin/minioadmin)

- **PostgreSQL**: Banco de dados de metadados do Airflow
  - Port: 5432 (interno)

- **Airflow**: Orquestração de pipelines
  - Webserver: http://localhost:8080 (admin/admin)
  - Scheduler: Executa DAGs agendadas
  - Init: Inicializa banco de dados e usuário admin

- **JupyterLab**: Análise interativa
  - http://localhost:8888 (token: b3data)

### Dockerfile.airflow

Imagem customizada do Airflow que inclui:

- Apache Airflow 2.9.1 com Python 3.11
- OpenJDK 17 (para Spark)
- Todas as dependências do projeto (requirements.txt)
- Código da plataforma B3 pré-instalado

### .dockerignore

Define arquivos/pastas excluídos do contexto de build:

- Dados locais (j_data)
- Logs (k_logs)
- Outputs (z_outputs)
- Cache Python e notebooks

## Como Usar

### Opção 1: Setup Script (Recomendado)

```bash
# Da raiz do projeto
./setup.sh setup     # Setup completo
./setup.sh up        # Só iniciar containers
./setup.sh down      # Parar containers
./setup.sh status    # Status dos containers
./setup.sh logs      # Ver logs
./setup.sh destroy   # Parar e remover volumes
```

### Opção 2: Docker Compose Manual

```bash
# Da raiz do projeto
docker compose -f z_infra/docker-compose.yml up -d --build

# Ou entrar na pasta z_infra
cd z_infra
docker compose up -d --build
```

## Volumes Persistentes

Os seguintes volumes são criados para persistir dados entre reinicializações:

- `minio_data`: Dados S3 (Bronze/Silver/Gold)
- `postgres_data`: Metadados do Airflow
- `airflow_logs`: Logs de execução das DAGs

Para destruir os volumes:

```bash
# Da raiz do projeto
./setup.sh destroy

# Ou manualmente
docker compose -f z_infra/docker-compose.yml down -v
```

## Contexto de Build

O Dockerfile.airflow usa o **diretório pai** como contexto de build (`context: ..`),
permitindo acesso a:

- requirements.txt
- Todo código Python da plataforma (a_configs, b_models, etc.)

## Troubleshooting

### Containers não iniciam

```bash
# Verificar logs
./setup.sh logs
# Ou de um serviço específico
docker compose -f z_infra/docker-compose.yml logs airflow_webserver

# Verificar status
docker compose -f z_infra/docker-compose.yml ps
```

### Reconstruir imagens

```bash
# Parar tudo
./setup.sh down

# Reconstruir sem cache
docker compose -f z_infra/docker-compose.yml build --no-cache

# Iniciar novamente
./setup.sh up
```

### Espaço em disco

```bash
# Limpar containers e imagens não utilizadas
docker system prune -a --volumes

# CUIDADO: Isso remove TODOS os dados!
```

## Portas Utilizadas

| Serviço       | Porta | URL                     |
| ------------- | ----- | ----------------------- |
| MinIO API     | 9000  | http://localhost:9000   |
| MinIO Console | 9001  | http://localhost:9001   |
| Airflow UI    | 8080  | http://localhost:8080   |
| JupyterLab    | 8888  | http://localhost:8888   |
| PostgreSQL    | 5432  | (interno - não exposto) |

Certifique-se de que essas portas estão disponíveis antes de iniciar os containers.
