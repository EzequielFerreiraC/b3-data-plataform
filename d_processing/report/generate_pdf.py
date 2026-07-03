"""
PDF Report Generator — B3 Data Platform.

Generates analytical PDF reports from Gold layer data using FPDF2 + Matplotlib.
Output format: relatorio_YYMMDD_HHMM.pdf
"""
from __future__ import annotations

import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/CI

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import polars as pl
from fpdf import FPDF

from a_configs.logger import get_logger
from a_configs.settings import OUTPUTS_PATH

logger = get_logger(__name__)

# Style
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 9})


# ---------------------------------------------------------------------------
# Chart Generators (return temp file paths)
# ---------------------------------------------------------------------------


def _chart_cumulative_returns(df: pl.DataFrame, top_n: int = 6) -> str:
    """Line chart: cumulative returns over time for top N tickers."""
    top_tickers = (
        df.group_by("ticker")
        .agg(pl.col("cum_return").last().alias("final_return"))
        .sort("final_return", descending=True)
        .head(top_n)["ticker"]
        .to_list()
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    for ticker in top_tickers:
        ticker_df = df.filter(pl.col("ticker") == ticker).sort("trade_date")
        ax.plot(
            ticker_df["trade_date"].to_list(),
            ticker_df["cum_return"].to_list(),
            label=ticker.replace(".SA", ""),
            linewidth=1.5,
        )

    ax.set_title("Retorno Acumulado — Top Ativos", fontsize=12, fontweight="bold")
    ax.set_xlabel("Data")
    ax.set_ylabel("Retorno Acumulado")
    ax.legend(loc="upper left", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    fig.autofmt_xdate()
    plt.tight_layout()

    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_volatility(df: pl.DataFrame) -> str:
    """Bar chart: average 20-day volatility by ticker."""
    vol_df = (
        df.group_by("ticker")
        .agg(pl.col("volatility_20d").mean().alias("avg_vol"))
        .sort("avg_vol", descending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 4.5))
    tickers = [t.replace(".SA", "") for t in vol_df["ticker"].to_list()]
    values = vol_df["avg_vol"].to_list()

    colors = sns.color_palette("RdYlGn_r", n_colors=len(tickers))
    ax.barh(tickers, values, color=colors)
    ax.set_title("Volatilidade Média Anualizada (20d)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Volatilidade")
    plt.tight_layout()

    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_volume_comparison(df: pl.DataFrame) -> str:
    """Bar chart: average daily volume by ticker."""
    vol_df = (
        df.group_by("ticker")
        .agg(pl.col("volume").mean().alias("avg_volume"))
        .sort("avg_volume", descending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 4.5))
    tickers = [t.replace(".SA", "") for t in vol_df["ticker"].to_list()]
    values = [v / 1_000_000 for v in vol_df["avg_volume"].to_list()]

    ax.barh(tickers, values, color=sns.color_palette("Blues_d", n_colors=len(tickers)))
    ax.set_title("Volume Médio Diário (milhões)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Volume (M)")
    plt.tight_layout()

    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_monthly_returns_heatmap(monthly_df: pl.DataFrame) -> str:
    """Heatmap: monthly returns by ticker."""
    if monthly_df.is_empty():
        return ""

    pivot = monthly_df.pivot(
        on="month",
        index="ticker",
        values="month_return",
    ).sort("ticker")

    tickers = [t.replace(".SA", "") for t in pivot["ticker"].to_list()]
    months = [c for c in pivot.columns if c != "ticker"]
    data = pivot.select(months).to_numpy()

    fig, ax = plt.subplots(figsize=(10, max(4, len(tickers) * 0.5)))
    sns.heatmap(
        data * 100,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        center=0,
        xticklabels=[f"Mês {m}" for m in months],
        yticklabels=tickers,
        ax=ax,
        cbar_kws={"label": "Retorno (%)"},
    )
    ax.set_title("Retorno Mensal por Ativo (%)", fontsize=12, fontweight="bold")
    plt.tight_layout()

    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# PDF Builder
# ---------------------------------------------------------------------------


class B3ReportPDF(FPDF):
    """Custom PDF with header/footer for B3 reports."""

    def __init__(self, report_date: datetime):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_date = report_date
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "B3 Data Platform — Relatório Analítico", align="L")
        self.cell(0, 8, self.report_date.strftime("%d/%m/%Y %H:%M"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def add_cover(self):
        """Add a cover page."""
        self.add_page()
        self.ln(60)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(30, 60, 120)
        self.cell(0, 15, "Relatório Analítico", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 16)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, "B3 — Bolsa de Valores do Brasil", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_font("Helvetica", "", 12)
        self.cell(
            0, 8,
            f"Gerado em: {self.report_date.strftime('%d/%m/%Y às %H:%M')}",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.ln(30)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "Dados processados via Medallion Architecture", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "(Bronze → Silver → Gold)", align="C", new_x="LMARGIN", new_y="NEXT")

    def add_section(self, title: str):
        """Add section title."""
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 60, 120)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(8)

    def add_chart(self, image_path: str, caption: str = ""):
        """Embed a chart image."""
        if not image_path or not Path(image_path).exists():
            return
        available_width = self.w - self.l_margin - self.r_margin
        self.image(image_path, w=available_width)
        if caption:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 6, caption, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def add_summary_table(self, summary_df: pl.DataFrame):
        """Add portfolio summary table."""
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(30, 60, 120)
        self.set_text_color(255, 255, 255)

        col_widths = [22, 28, 28, 25, 30, 30, 27]
        headers = ["Ticker", "Início", "Fim", "Retorno", "Vol. Média", "Volatilidade", "Máx. Preço"]

        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, align="C", fill=True)
        self.ln()

        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 0)

        for row in summary_df.head(12).iter_rows(named=True):
            self.set_fill_color(245, 245, 250)
            fill = self.page_no() % 2 == 0

            ticker = row.get("ticker", "").replace(".SA", "")
            first_date = row.get("first_date")
            last_date = row.get("last_date")
            total_return = row.get("total_return", 0)
            avg_vol = row.get("avg_daily_volume", 0)
            avg_volatility = row.get("avg_volatility", 0)
            period_high = row.get("period_high", 0)

            first_str = first_date.strftime("%d/%m/%y") if first_date else "-"
            last_str = last_date.strftime("%d/%m/%y") if last_date else "-"

            self.cell(col_widths[0], 6, ticker, border=1, align="C")
            self.cell(col_widths[1], 6, first_str, border=1, align="C")
            self.cell(col_widths[2], 6, last_str, border=1, align="C")
            self.cell(col_widths[3], 6, f"{(total_return or 0)*100:.2f}%", border=1, align="C")
            self.cell(col_widths[4], 6, f"{(avg_vol or 0)/1e6:.1f}M", border=1, align="C")
            self.cell(col_widths[5], 6, f"{(avg_volatility or 0)*100:.1f}%", border=1, align="C")
            self.cell(col_widths[6], 6, f"R${(period_high or 0):.2f}", border=1, align="C")
            self.ln()


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------


def generate_report(
    daily_metrics: pl.DataFrame,
    portfolio_summary: pl.DataFrame,
    monthly_returns: pl.DataFrame,
    output_dir: Path | None = None,
    report_date: datetime | None = None,
) -> Path:
    """
    Generate a full PDF report from Gold layer data.

    Returns the path to the generated PDF file.
    Naming: relatorio_YYMMDD_HHMM.pdf
    """
    report_date = report_date or datetime.now(timezone.utc)
    output_dir = output_dir or OUTPUTS_PATH
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build filename: relatorio_YYMMDD_HHMM.pdf
    filename = f"relatorio_{report_date.strftime('%y%m%d_%H%M')}.pdf"
    output_path = output_dir / filename

    logger.info("Generating PDF report", extra={"output": str(output_path)})

    # Initialize PDF
    pdf = B3ReportPDF(report_date=report_date)
    pdf.alias_nb_pages()

    # Cover
    pdf.add_cover()

    # Section 1: Portfolio Summary Table
    if not portfolio_summary.is_empty():
        pdf.add_section("Resumo do Portfólio")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, (
            "Visão geral dos ativos monitorados no período, incluindo retorno acumulado, "
            "volume médio e volatilidade anualizada."
        ))
        pdf.ln(5)
        pdf.add_summary_table(portfolio_summary)

    # Section 2: Cumulative Returns
    if not daily_metrics.is_empty():
        pdf.add_section("Retorno Acumulado")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, (
            "Evolução do retorno acumulado dos principais ativos ao longo do período analisado."
        ))
        pdf.ln(3)
        chart_path = _chart_cumulative_returns(daily_metrics)
        pdf.add_chart(chart_path, "Retorno acumulado dos top 6 ativos")

    # Section 3: Volatility
    if not daily_metrics.is_empty():
        pdf.add_section("Análise de Volatilidade")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, (
            "Volatilidade média anualizada (janela de 20 dias) para cada ativo. "
            "Valores mais altos indicam maior risco."
        ))
        pdf.ln(3)
        chart_path = _chart_volatility(daily_metrics)
        pdf.add_chart(chart_path, "Volatilidade anualizada — média do período")

    # Section 4: Volume
    if not daily_metrics.is_empty():
        pdf.add_section("Volume de Negociação")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, "Volume médio diário de negociação por ativo (em milhões de ações).")
        pdf.ln(3)
        chart_path = _chart_volume_comparison(daily_metrics)
        pdf.add_chart(chart_path, "Volume médio diário (milhões)")

    # Section 5: Monthly Returns Heatmap
    if not monthly_returns.is_empty():
        pdf.add_section("Retornos Mensais")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, (
            "Mapa de calor com os retornos mensais (%) de cada ativo. "
            "Verde indica retorno positivo, vermelho negativo."
        ))
        pdf.ln(3)
        chart_path = _chart_monthly_returns_heatmap(monthly_returns)
        pdf.add_chart(chart_path, "Heatmap de retornos mensais (%)")

    # Save
    pdf.output(str(output_path))
    logger.info("PDF report generated", extra={"path": str(output_path), "pages": pdf.page_no()})

    # Cleanup temp chart files
    import glob
    import os
    for f in glob.glob(tempfile.gettempdir() + "/tmp*.png"):
        try:
            os.unlink(f)
        except OSError:
            pass

    return output_path
