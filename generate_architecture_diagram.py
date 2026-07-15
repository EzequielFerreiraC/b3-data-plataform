"""
Gerador de Diagrama de Arquitetura — B3 Data Platform
Gera um PNG com fundo transparente mostrando a arquitetura Medallion.

Uso:
    python generate_architecture_diagram.py
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ──────────────────────────────────────────────────────────────────────
# Paleta
# ──────────────────────────────────────────────────────────────────────
C = {
    # Camadas medallion
    "source":       "#6366F1",
    "source_lt":    "#EEF2FF",
    "ingestion":    "#8B5CF6",
    "ingestion_lt": "#F5F3FF",
    "bronze":       "#D97706",
    "bronze_lt":    "#FFFBEB",
    "silver":       "#6B7280",
    "silver_lt":    "#F3F4F6",
    "gold":         "#B45309",
    "gold_lt":      "#FEF3C7",
    "report":       "#059669",
    "report_lt":    "#ECFDF5",
    "valid":        "#DC2626",
    "valid_lt":     "#FEF2F2",
    # Infra
    "infra":        "#0EA5E9",
    "infra_lt":     "#F0F9FF",
    # Texto
    "dark":         "#1E293B",
    "muted":        "#64748B",
    "arrow":        "#94A3B8",
    "arrow_main":   "#475569",
}

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _box(ax, x, y, w, h, title, sub=None, color="#6366F1", bg="#EEF2FF",
         fs=11, sub_fs=8.5, lw=2.2, radius=0.015, title_color=None):
    """Caixa arredondada com título e subtítulo opcional."""
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        fc=bg, ec=color, lw=lw, zorder=2,
    )
    ax.add_patch(patch)

    tc = title_color or C["dark"]
    if sub:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=tc, zorder=3)
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                fontsize=sub_fs, color=C["muted"], linespacing=1.4, zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=tc, zorder=3)


def _band(ax, y, h, color, alpha=0.07):
    """Faixa horizontal de fundo."""
    p = FancyBboxPatch((1, y), 18, h, boxstyle="round,pad=0,rounding_size=0.12",
                       fc=color, ec="none", alpha=alpha, zorder=0)
    ax.add_patch(p)


def _label_band(ax, x, y, text, color, fs=9):
    """Label rotacionado na lateral da band."""
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=color, alpha=0.55, rotation=90, zorder=1)


def _arrow(ax, x1, y1, x2, y2, color="#475569", lw=2, head=14):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", color=color,
        lw=lw, mutation_scale=head, zorder=1, shrinkA=0, shrinkB=0,
    ))


def _arrow_label(ax, x, y, text, color="#64748B", fs=7.5):
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=color, style="italic", zorder=4)


# ──────────────────────────────────────────────────────────────────────
# Diagrama principal — HORIZONTAL (esquerda → direita)
# ──────────────────────────────────────────────────────────────────────
def draw_diagram():
    fig, ax = plt.subplots(figsize=(32, 18))
    fig.patch.set_alpha(0.0)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 22)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Título ──────────────────────────────────────────────────────
    ax.text(20, 21.4, "B3 Data Platform  —  Medallion Lakehouse Architecture",
            ha="center", va="center", fontsize=24, fontweight="bold", color=C["dark"])
    ax.text(20, 20.8, "Python 3.11  |  Polars  |  Airflow  |  MinIO  |  Docker Compose",
            ha="center", va="center", fontsize=11, color=C["muted"])
    ax.plot([6, 34], [20.45, 20.45], color=C["arrow"], lw=1, alpha=0.25, zorder=0)

    # ── Layout principal: 6 colunas (Sources → Ingest → Bronze → Silver → Gold → Report)
    # Cada camada é uma coluna vertical de caixas
    # col_x: centro X de cada coluna
    col_x = [3.0, 9.5, 16.0, 23.0, 30.0, 37.0]
    col_w = 5.0   # largura padrão das caixas
    bh = 1.5      # altura padrão

    # ── Faixas verticais de fundo ──
    band_w = 5.8
    layers = [
        (C["source"],    "SOURCES"),
        (C["ingestion"], "INGEST"),
        (C["bronze"],    "BRONZE"),
        (C["silver"],    "SILVER"),
        (C["gold"],      "GOLD"),
        (C["report"],    "REPORT"),
    ]
    for i, (color, label) in enumerate(layers):
        bx = col_x[i] - band_w / 2
        band = FancyBboxPatch(
            (bx, 4.0), band_w, 16.0,
            boxstyle="round,pad=0,rounding_size=0.15",
            fc=color, ec="none", alpha=0.06, zorder=0,
        )
        ax.add_patch(band)
        ax.text(col_x[i], 19.7, label, ha="center", va="center",
                fontsize=10, fontweight="bold", color=color, alpha=0.6)

    # ================================================================
    #  COLUNA 1 — SOURCES
    # ================================================================
    cx = col_x[0]
    hw = col_w / 2

    _box(ax, cx - hw, 16.5, col_w, bh, "Yahoo Finance",
         "yfinance\nOHLCV diario\n12 tickers .SA",
         C["source"], C["source_lt"], fs=10.5)

    _box(ax, cx - hw, 14.2, col_w, bh, "BRAPI",
         "brapi.dev\nAPI brasileira\nBearer token",
         C["source"], C["source_lt"], fs=10.5)

    # ================================================================
    #  COLUNA 2 — INGESTION
    # ================================================================
    cx = col_x[1]

    _box(ax, cx - hw, 16.5, col_w, bh, "c_ingestion/",
         "yahoo_finance.py\nbrapi.py",
         C["ingestion"], C["ingestion_lt"], fs=10.5)

    _box(ax, cx - hw, 14.2, col_w, bh, "b_models/schemas.py",
         "RawTrade (Pydantic)\nCleanTrade (Pydantic)\nSpark StructTypes",
         C["ingestion"], C["ingestion_lt"], fs=10.5)

    # Seta entre schemas → ingestion (para cima)
    _arrow(ax, cx, 15.7, cx, 16.5, C["arrow"], lw=1.2, head=10)
    _arrow_label(ax, cx + 0.8, 16.05, "validacao", C["ingestion"])

    # ================================================================
    #  COLUNA 3 — BRONZE
    # ================================================================
    cx = col_x[2]

    _box(ax, cx - hw, 17.2, col_w, 1.8, "BronzePipeline",
         "f_pipelines/bronze_pipeline.py\nextract() -> load()\nNo transformation",
         C["bronze"], C["bronze_lt"], fs=10.5)

    _box(ax, cx - hw, 14.8, col_w, 1.8, "bronze/ingest.py",
         "d_processing/\nwrite_parquet(snappy)\npartition by trade_date",
         C["bronze"], C["bronze_lt"], fs=10.5)

    _box(ax, cx - hw, 12.4, col_w, 1.8, "j_data/bronze/",
         "Parquet bruto imutavel\n+ source + ingested_at\ntrade_date_YYMMDD_HHMM/",
         C["bronze"], C["bronze_lt"], fs=10.5, title_color=C["bronze"])

    # Setas internas (vertical)
    _arrow(ax, cx, 17.2, cx, 16.6, C["bronze"], lw=2, head=12)
    _arrow(ax, cx, 14.8, cx, 14.2, C["bronze"], lw=2, head=12)

    # ================================================================
    #  COLUNA 4 — SILVER
    # ================================================================
    cx = col_x[3]

    _box(ax, cx - hw, 17.2, col_w, 1.8, "SilverPipeline",
         "f_pipelines/silver_pipeline.py\nextract -> transform\n-> validate -> load",
         C["silver"], C["silver_lt"], fs=10.5)

    _box(ax, cx - hw, 14.8, col_w, 1.8, "silver/transform.py",
         "cast_types | remove_nulls\ndedup | invalid_prices\ncalculate_daily_return",
         C["silver"], C["silver_lt"], fs=10.5)

    _box(ax, cx - hw, 12.8, col_w, 1.2, "quality_checks.py",
         "nulls | prices>0 | dupes | dates\nfail-fast assertions",
         C["valid"], C["valid_lt"], fs=10, lw=1.8)

    _box(ax, cx - hw, 10.7, col_w, 1.5, "j_data/silver/",
         "Parquet limpo\n+ daily_return + processed_at",
         C["silver"], C["silver_lt"], fs=10.5, title_color=C["silver"])

    _arrow(ax, cx, 17.2, cx, 16.6, C["silver"], lw=2, head=12)
    _arrow(ax, cx, 14.8, cx, 14.0, C["silver"], lw=1.5, head=10)
    _arrow(ax, cx, 12.8, cx, 12.2, C["silver"], lw=1.5, head=10)

    # ================================================================
    #  COLUNA 5 — GOLD
    # ================================================================
    cx = col_x[4]

    _box(ax, cx - hw, 17.2, col_w, 1.8, "GoldPipeline",
         "f_pipelines/gold_pipeline.py\nextract -> aggregate\n-> load (3 tabelas)",
         C["gold"], C["gold_lt"], fs=10.5)

    _box(ax, cx - hw, 15.7, col_w, 1.1, "daily_metrics",
         "OHLCV + vol_20d + cum_return",
         C["gold"], C["gold_lt"], fs=9.5, sub_fs=8)

    _box(ax, cx - hw, 14.3, col_w, 1.1, "portfolio_summary",
         "1 row/ticker | retorno total | max drawdown",
         C["gold"], C["gold_lt"], fs=9.5, sub_fs=8)

    _box(ax, cx - hw, 12.9, col_w, 1.1, "monthly_returns",
         "OHLC mensal | retorno mensal",
         C["gold"], C["gold_lt"], fs=9.5, sub_fs=8)

    _box(ax, cx - hw, 11.0, col_w, 1.5, "j_data/gold/",
         "3 tabelas analiticas\nParquet otimizado",
         C["gold"], C["gold_lt"], fs=10.5, title_color=C["gold"])

    _arrow(ax, cx, 17.2, cx, 16.8, C["gold"], lw=1.5, head=10)
    _arrow(ax, cx, 12.9, cx, 12.5, C["gold"], lw=2, head=12)

    # ================================================================
    #  COLUNA 6 — REPORT
    # ================================================================
    cx = col_x[5]

    _box(ax, cx - hw, 17.2, col_w, 1.8, "ReportPipeline",
         "f_pipelines/report_pipeline.py\nread gold -> charts -> PDF",
         C["report"], C["report_lt"], fs=10.5)

    _box(ax, cx - hw, 14.8, col_w, 1.8, "generate_pdf.py",
         "d_processing/report/\nMatplotlib | Seaborn\nFPDF2",
         C["report"], C["report_lt"], fs=10.5)

    _box(ax, cx - hw, 12.4, col_w, 1.8, "z_outputs/",
         "relatorio_YYMMDD_HHMM.pdf\nRetorno | Volatilidade\nRanking ativos",
         C["report"], C["report_lt"], fs=10.5, title_color=C["report"])

    _arrow(ax, cx, 17.2, cx, 16.6, C["report"], lw=2, head=12)
    _arrow(ax, cx, 14.8, cx, 14.2, C["report"], lw=2, head=12)

    # ================================================================
    #  SETAS HORIZONTAIS entre colunas (fluxo principal →)
    # ================================================================
    arrow_y = 17.3  # linha principal do pipeline
    pairs = [
        (col_x[0], col_x[1]),  # Sources → Ingest
        (col_x[1], col_x[2]),  # Ingest → Bronze
        (col_x[2], col_x[3]),  # Bronze → Silver
        (col_x[3], col_x[4]),  # Silver → Gold
        (col_x[4], col_x[5]),  # Gold → Report
    ]
    for x1, x2 in pairs:
        _arrow(ax, x1 + hw + 0.15, arrow_y, x2 - hw - 0.15, arrow_y,
               C["arrow_main"], lw=3, head=16)

    # Labels nas setas horizontais
    labels_h = [
        "requests",
        "Polars DF",
        "read_bronze()",
        "read_silver()",
        "read gold",
    ]
    for i, lab in enumerate(labels_h):
        mx = (pairs[i][0] + pairs[i][1]) / 2
        _arrow_label(ax, mx, arrow_y + 0.4, lab, C["arrow_main"], fs=8)

    # ================================================================
    #  INFRAESTRUTURA — barra inferior
    # ================================================================
    infra_y = 0.3
    infra_h = 3.5
    infra_band = FancyBboxPatch(
        (0.5, infra_y), 39, infra_h,
        boxstyle="round,pad=0,rounding_size=0.15",
        fc=C["infra"], ec="none", alpha=0.05, zorder=0,
    )
    ax.add_patch(infra_band)

    ax.text(20, 3.5, "Infraestrutura  &  Tech Stack",
            ha="center", va="center", fontsize=13, fontweight="bold", color=C["infra"])
    ax.plot([4, 36], [3.2, 3.2], color=C["infra"], lw=0.7, alpha=0.3, zorder=0)

    # Caixas de infra
    iw = 5.5
    ih = 1.8
    iy = 1.0
    igap = 1.1

    infra_items = [
        ("Apache Airflow",  "LocalExecutor | PostgreSQL 15\n4 DAGs | Mon-Fri 22:00 UTC"),
        ("MinIO (S3)",      "Object Storage S3-compatible\nb3-bronze | b3-silver | b3-gold"),
        ("Docker Compose",  "5 containers: MinIO, Postgres\nAirflow (web + scheduler + init)"),
        ("Tech Stack",      "Polars | PySpark | Pydantic v2\nyfinance | Matplotlib | FPDF2"),
        ("Tests & Quality", "pytest (4 suites) | Ruff linter\nGreat Expectations"),
        ("Jupyter",         "4 Notebooks exploratorios\n01_bronze | 02_silver | 03_gold"),
    ]

    total_w = len(infra_items) * iw + (len(infra_items) - 1) * igap
    start_x = (40 - total_w) / 2

    for i, (title, desc) in enumerate(infra_items):
        ix = start_x + i * (iw + igap)
        _box(ax, ix, iy, iw, ih, title, desc,
             C["infra"], C["infra_lt"], fs=10, sub_fs=8.5, lw=1.5)

    # ── Airflow DAGs sequenciais (pequeno detalhe) ──
    ax.text(20, 4.6, "Pipeline Sequence:  b3_bronze_dag  -->  b3_silver_dag  -->  b3_gold_dag  -->  b3_report_dag",
            ha="center", va="center", fontsize=9, color=C["infra"],
            fontfamily="monospace", alpha=0.7)

    # ── Tickers ──
    ax.text(20, 4.15, "Tickers:  PETR4  VALE3  ITUB4  BBDC4  ABEV3  WEGE3  RENT3  MGLU3  BPAC11  LREN3  BBAS3  RADL3",
            ha="center", va="center", fontsize=8.5, color=C["muted"],
            fontfamily="monospace")

    # ── Salvar ──
    out = "z_outputs/arquitetura_b3_platform.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", transparent=True, pad_inches=0.4)
    plt.close(fig)
    print(f"Diagrama salvo em: {out}")
    return out


if __name__ == "__main__":
    draw_diagram()
