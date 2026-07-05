#!/usr/bin/env bash
# =============================================================================
# B3 Data Platform — Setup & Management Script
# Cross-platform (Linux/macOS/WSL/Git Bash on Windows)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Colors & Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# Dependency Checks
# ---------------------------------------------------------------------------
check_docker() {
    if ! command -v docker &>/dev/null; then
        error "Docker not found. Install: https://docs.docker.com/get-docker/"
        return 1
    fi
    if ! docker info &>/dev/null; then
        error "Docker daemon is not running. Start Docker Desktop or the Docker service."
        return 1
    fi
    success "Docker is available"
}

check_docker_compose() {
    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        error "Docker Compose not found. Install: https://docs.docker.com/compose/install/"
        return 1
    fi
    success "Docker Compose is available ($COMPOSE_CMD)"
}

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        error "Python 3.11+ not found. Install: https://www.python.org/downloads/"
        return 1
    fi

    local version
    version=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
    if [[ $(echo "$version < 3.11" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        warn "Python $version detected. 3.11+ recommended."
    else
        success "Python is available ($PYTHON_CMD $version)"
    fi
}

check_all_deps() {
    info "Checking dependencies..."
    echo ""
    check_docker
    check_docker_compose
    check_python
    echo ""
    success "All dependencies OK"
}

# ---------------------------------------------------------------------------
# Environment Setup
# ---------------------------------------------------------------------------
setup_env() {
    if [ ! -f ".env" ]; then
        info "Creating .env from .env.example..."
        cp .env.example .env
        success ".env created — edit it with your credentials if needed"
    else
        success ".env already exists"
    fi
}

setup_python_env() {
    info "Setting up Python virtual environment..."

    if [ ! -d ".venv" ]; then
        $PYTHON_CMD -m venv .venv
        success "Virtual environment created (.venv)"
    else
        success "Virtual environment already exists"
    fi

    # Activate — detect actual venv layout
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        error "Cannot find venv activate script"
        return 1
    fi

    info "Installing Python dependencies..."
    $PYTHON_CMD -m pip install --upgrade pip -q 2>/dev/null || true
    $PYTHON_CMD -m pip install -r requirements.txt -q
    success "Python dependencies installed"
}

# ---------------------------------------------------------------------------
# Docker Operations
# ---------------------------------------------------------------------------
containers_up() {
    info "Building and starting all containers..."
    $COMPOSE_CMD up -d --build
    echo ""
    success "All containers are running!"
    echo ""
    info "Services:"
    echo -e "  ${CYAN}Airflow UI:${NC}    http://localhost:8080  (admin/admin)"
    echo -e "  ${CYAN}MinIO Console:${NC} http://localhost:9001  (minioadmin/minioadmin)"
    echo -e "  ${CYAN}JupyterLab:${NC}    http://localhost:8888  (token: b3data)"
    echo ""
}

containers_down() {
    info "Stopping all containers..."
    $COMPOSE_CMD down
    success "All containers stopped"
}

containers_restart() {
    info "Restarting all containers..."
    $COMPOSE_CMD restart
    success "All containers restarted"
}

containers_destroy() {
    warn "This will stop containers AND delete volumes (all data will be lost)!"
    read -rp "Are you sure? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        $COMPOSE_CMD down -v
        success "Containers and volumes destroyed"
    else
        info "Cancelled"
    fi
}

containers_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        $COMPOSE_CMD logs -f "$service"
    else
        $COMPOSE_CMD logs -f --tail=50
    fi
}

containers_status() {
    $COMPOSE_CMD ps
}

# ---------------------------------------------------------------------------
# Data Directories
# ---------------------------------------------------------------------------
setup_directories() {
    info "Creating project directories..."
    mkdir -p j_data/bronze j_data/silver j_data/gold
    mkdir -p k_logs
    mkdir -p z_outputs
    success "Directories ready"
}

# ---------------------------------------------------------------------------
# Full Setup
# ---------------------------------------------------------------------------
full_setup() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║     B3 Data Platform — Full Setup           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_all_deps
    setup_env
    setup_directories
    setup_python_env
    containers_up

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Setup complete! Platform is running.     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
}

# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------
run_pipeline() {
    local layer="${1:-all}"
    info "Running pipeline: $layer"

    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate 2>/dev/null || true
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate 2>/dev/null || true
    fi

    case "$layer" in
        bronze)
            $PYTHON_CMD -m f_pipelines.bronze_pipeline
            ;;
        silver)
            $PYTHON_CMD -m f_pipelines.silver_pipeline
            ;;
        gold)
            $PYTHON_CMD -m f_pipelines.gold_pipeline
            ;;
        report)
            $PYTHON_CMD -m f_pipelines.report_pipeline
            ;;
        all)
            $PYTHON_CMD -m f_pipelines.bronze_pipeline
            $PYTHON_CMD -m f_pipelines.silver_pipeline
            $PYTHON_CMD -m f_pipelines.gold_pipeline
            $PYTHON_CMD -m f_pipelines.report_pipeline
            ;;
        *)
            error "Unknown pipeline: $layer (use: bronze|silver|gold|report|all)"
            return 1
            ;;
    esac
    success "Pipeline '$layer' complete"
}

# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
show_menu() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}       B3 Data Platform — Manager             ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Full setup (install everything)"
    echo -e "  ${GREEN}2)${NC} Start containers"
    echo -e "  ${GREEN}3)${NC} Stop containers"
    echo -e "  ${GREEN}4)${NC} Restart containers"
    echo -e "  ${GREEN}5)${NC} Container status"
    echo -e "  ${GREEN}6)${NC} View logs"
    echo -e "  ${GREEN}7)${NC} Destroy containers + volumes"
    echo ""
    echo -e "  ${BLUE}8)${NC} Run pipeline (Bronze → Silver → Gold → Report)"
    echo -e "  ${BLUE}9)${NC} Run single pipeline (choose layer)"
    echo ""
    echo -e "  ${YELLOW}10)${NC} Check dependencies"
    echo -e "  ${YELLOW}11)${NC} Setup Python environment only"
    echo ""
    echo -e "  ${RED}0)${NC} Exit"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
}

interactive_menu() {
    while true; do
        show_menu
        read -rp "Choose an option: " choice
        echo ""

        case "$choice" in
            1) full_setup ;;
            2) containers_up ;;
            3) containers_down ;;
            4) containers_restart ;;
            5) containers_status ;;
            6)
                read -rp "Service (blank for all): " svc
                containers_logs "$svc"
                ;;
            7) containers_destroy ;;
            8) run_pipeline all ;;
            9)
                read -rp "Layer (bronze/silver/gold/report): " layer
                run_pipeline "$layer"
                ;;
            10) check_all_deps ;;
            11) setup_python_env ;;
            0)
                info "Bye!"
                exit 0
                ;;
            *)
                error "Invalid option: $choice"
                ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# CLI Arguments
# ---------------------------------------------------------------------------
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup       Full automated setup"
    echo "  up          Start containers"
    echo "  down        Stop containers"
    echo "  restart     Restart containers"
    echo "  status      Show container status"
    echo "  logs [svc]  View logs (optional: service name)"
    echo "  destroy     Stop + remove volumes"
    echo "  run [layer] Run pipeline (bronze|silver|gold|report|all)"
    echo "  deps        Check dependencies"
    echo "  help        Show this help"
    echo ""
    echo "Without arguments, opens interactive menu."
}

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
main() {
    COMPOSE_CMD="docker compose"  # default, overridden by check

    if [ $# -eq 0 ]; then
        check_docker_compose 2>/dev/null || COMPOSE_CMD="docker-compose"
        check_python 2>/dev/null || PYTHON_CMD="python3"
        interactive_menu
        exit 0
    fi

    check_docker_compose 2>/dev/null || COMPOSE_CMD="docker-compose"
    check_python 2>/dev/null || PYTHON_CMD="python3"

    case "${1:-}" in
        setup)    full_setup ;;
        up)       containers_up ;;
        down)     containers_down ;;
        restart)  containers_restart ;;
        status)   containers_status ;;
        logs)     containers_logs "${2:-}" ;;
        destroy)  containers_destroy ;;
        run)      run_pipeline "${2:-all}" ;;
        deps)     check_all_deps ;;
        help|-h|--help) show_help ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
