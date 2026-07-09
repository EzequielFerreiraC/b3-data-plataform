"""
PDF Report Generator - B3 Data Platform.

Generates analytical PDF reports from Gold layer data using FPDF2 + Matplotlib.
Charts replicate the same visualizations from the project notebooks.
Output format: report_YYMMDD_HHMM.pdf
"""
from __future__ import annotations

import glob
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import polars as pl
from fpdf import FPDF

from a_configs.logger import get_logger
from a_configs.settings import OUTPUTS_PATH

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Style (matching notebooks)
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "#fafafa",
    "grid.alpha": 0.3,
})

TOP5 = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA"]


def _save_fig(fig) -> str:
    """Save figure to temp PNG and return path."""
    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Charts from Notebook 03 - Gold Analytics
# ---------------------------------------------------------------------------


def chart_cumulative_return(daily: pl.DataFrame) -> str:
    """Retorno Acumulado por Ativo (from 03_gold_analytics cell 5)."""
    top_tickers = (
        daily.group_by("ticker")
        .agg(pl.col("cum_return").last().alias("final"))
        .sort("final", descending=True)
        .head(5)["ticker"].to_list()
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    for ticker in top_tickers:
        t_df = daily.filter(pl.col("ticker") == ticker).sort("trade_date")
        ax.plot(
            t_df["trade_date"].to_list(),
            [v * 100 for v in t_df["cum_return"].to_list()],
            label=ticker.replace(".SA", ""),
            linewidth=2,
        )

    ax.axhline(y=0, linestyle="--", color="grey", linewidth=0.8)
    ax.set_title("Retorno Acumulado por Ativo", fontweight="bold")
    ax.set_xlabel("Data")
    ax.set_ylabel("Retorno Acumulado (%)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    fig.autofmt_xdate()
    plt.tight_layout()
    return _save_fig(fig)


def chart_volatility_20d(daily: pl.DataFrame) -> str:
    """Volatilidade Anualizada - Janela Movel de 20 dias (from 03_gold cell 6)."""
    plot_df = daily.filter(pl.col("ticker").is_in(TOP5)).sort("trade_date")

    fig, ax = plt.subplots(figsize=(11, 5))
    for ticker in TOP5:
        t_df = plot_df.filter(pl.col("ticker") == ticker)
        if t_df.is_empty():
            continue
        ax.plot(
            t_df["trade_date"].to_list(),
            [v * 100 if v is not None else 0 for v in t_df["volatility_20d"].to_list()],
            label=ticker.replace(".SA", ""),
            linewidth=1.8,
        )

    ax.set_title("Volatilidade Anualizada - Janela de 20 dias", fontweight="bold")
    ax.set_xlabel("Data")
    ax.set_ylabel("Volatilidade (%)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    fig.autofmt_xdate()
    plt.tight_layout()
    return _save_fig(fig)


def chart_risk_vs_return(summary: pl.DataFrame) -> str:
    """Risco x Retorno (from 03_gold cell 8)."""
    df = summary.drop_nulls(subset=["total_return", "avg_volatility"])
    if df.is_empty():
        return ""

    fig, ax = plt.subplots(figsize=(9, 6))
    x = [v * 100 for v in df["avg_volatility"].to_list()]
    y = [v * 100 for v in df["total_return"].to_list()]
    tickers = [t.replace(".SA", "") for t in df["ticker"].to_list()]

    colors = sns.color_palette("husl", n_colors=len(tickers))
    ax.scatter(x, y, s=120, c=colors, edgecolors="DarkSlateGrey", linewidth=1, zorder=5)

    for i, txt in enumerate(tickers):
        ax.annotate(txt, (x[i], y[i]), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=8, fontweight="bold")

    ax.axhline(y=0, linestyle="--", color="grey", linewidth=0.8)
    ax.set_title("Risco x Retorno no Periodo (por Ativo)", fontweight="bold")
    ax.set_xlabel("Volatilidade Media Anualizada (%)")
    ax.set_ylabel("Retorno Total (%)")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    plt.tight_layout()
    return _save_fig(fig)


def chart_monthly_heatmap(monthly: pl.DataFrame) -> str:
    """Mapa de Calor - Retorno Mensal (from 03_gold cell 10)."""
    if monthly.is_empty():
        return ""

    top_monthly = monthly.filter(pl.col("ticker").is_in(TOP5))
    if top_monthly.is_empty():
        top_monthly = monthly

    pivot = (
        top_monthly
        .with_columns(
            (pl.col("year").cast(pl.Utf8) + "-" + pl.col("month").cast(pl.Utf8).str.zfill(2)).alias("ym")
        )
        .pivot(values="month_return", index="ticker", on="ym")
        .sort("ticker")
    )

    tickers = [t.replace(".SA", "") for t in pivot["ticker"].to_list()]
    cols = [c for c in pivot.columns if c != "ticker"]
    data = pivot.select(cols).to_numpy().astype(float) * 100

    fig, ax = plt.subplots(figsize=(max(10, 1.1 * len(cols)), max(4, len(tickers) * 0.6)))
    sns.heatmap(
        data,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        center=0,
        linewidths=0.5,
        linecolor="white",
        xticklabels=cols,
        yticklabels=tickers,
        cbar_kws={"label": "Retorno Mensal (%)"},
        ax=ax,
    )
    ax.set_title("Mapa de Calor - Retorno Mensal por Ativo (%)", fontweight="bold", pad=12)
    ax.set_xlabel("Ano-Mes")
    ax.set_ylabel("Ativo")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    return _save_fig(fig)


# ---------------------------------------------------------------------------
# Charts from Notebook 04 - Exploration
# ---------------------------------------------------------------------------


def chart_correlation_matrix(daily: pl.DataFrame) -> str:
    """Matriz de Correlacao - Retornos Diarios (from 04_exploration cell 4)."""
    wide = (
        daily
        .select(["ticker", "trade_date", "daily_return"])
        .pivot(values="daily_return", index="trade_date", on="ticker")
        .sort("trade_date")
    )

    # Remove trade_date column and compute correlation
    cols = [c for c in wide.columns if c != "trade_date"]
    numeric_df = wide.select(cols).to_pandas().astype(float)
    corr = numeric_df.corr()

    labels = [c.replace(".SA", "") for c in corr.columns]
    corr.columns = labels
    corr.index = labels

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Coeficiente de Correlacao"},
        ax=ax,
        vmin=-1,
        vmax=1,
    )
    ax.set_title("Matriz de Correlacao - Retornos Diarios", fontweight="bold", pad=12)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    return _save_fig(fig)


def chart_bollinger_bands(daily: pl.DataFrame, ticker: str = "PETR4.SA") -> str:
    """Bandas de Bollinger (from 04_exploration cell 6)."""
    bb = (
        daily
        .filter(pl.col("ticker") == ticker)
        .sort("trade_date")
        .with_columns([
            pl.col("close_price").rolling_mean(window_size=20, min_samples=1).alias("sma_20"),
            pl.col("close_price").rolling_std(window_size=20, min_samples=2).alias("std_20"),
        ])
        .with_columns([
            (pl.col("sma_20") + 2 * pl.col("std_20")).alias("upper_band"),
            (pl.col("sma_20") - 2 * pl.col("std_20")).alias("lower_band"),
        ])
    )

    if bb.is_empty():
        return ""

    dates = bb["trade_date"].to_list()
    close = np.array(bb["close_price"].to_list(), dtype=float)
    sma = np.array([v if v is not None else np.nan for v in bb["sma_20"].to_list()], dtype=float)
    upper = np.array([v if v is not None else np.nan for v in bb["upper_band"].to_list()], dtype=float)
    lower = np.array([v if v is not None else np.nan for v in bb["lower_band"].to_list()], dtype=float)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.fill_between(dates, lower, upper, alpha=0.1, color="royalblue", label="Banda (2 sigma)")
    ax.plot(dates, upper, linestyle="--", color="indianred", linewidth=1, alpha=0.8, label="Banda Superior")
    ax.plot(dates, lower, linestyle="--", color="seagreen", linewidth=1, alpha=0.8, label="Banda Inferior")
    ax.plot(dates, sma, color="orange", linewidth=1.8, label="SMA 20")
    ax.plot(dates, close, color="royalblue", linewidth=2, label="Fechamento")

    ax.set_title(f"Bandas de Bollinger - {ticker.replace('.SA', '')}", fontweight="bold")
    ax.set_xlabel("Data")
    ax.set_ylabel("Preco (R$)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.autofmt_xdate()
    plt.tight_layout()
    return _save_fig(fig)


def chart_portfolio_backtest(daily: pl.DataFrame) -> str:
    """Retorno Acumulado - Portfolio Igualmente Ponderado (from 04_exploration cell 8)."""
    portfolio = (
        daily
        .group_by("trade_date")
        .agg(pl.col("daily_return").mean().alias("portfolio_return"))
        .sort("trade_date")
        .with_columns(
            ((1 + pl.col("portfolio_return").fill_null(0)).cum_prod() - 1).alias("portfolio_cum_return")
        )
    )

    if portfolio.is_empty():
        return ""

    dates = portfolio["trade_date"].to_list()
    cum_ret = [v * 100 for v in portfolio["portfolio_cum_return"].to_list()]

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(dates, cum_ret, color="#1f77b4", linewidth=2.4)
    ax.fill_between(dates, 0, cum_ret, alpha=0.08, color="#1f77b4")
    ax.axhline(y=0, linestyle="--", color="grey", linewidth=0.8)

    ax.set_title("Retorno Acumulado - Portfolio Igualmente Ponderado", fontweight="bold")
    ax.set_xlabel("Data")
    ax.set_ylabel("Retorno Acumulado (%)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.autofmt_xdate()
    plt.tight_layout()

    # Add final return annotation
    final_ret = cum_ret[-1] if cum_ret else 0
    ax.annotate(
        f"  {final_ret:.2f}%",
        xy=(dates[-1], cum_ret[-1]),
        fontsize=10, fontweight="bold", color="#1f77b4",
    )

    return _save_fig(fig)


# ---------------------------------------------------------------------------
# PDF Builder
# ---------------------------------------------------------------------------

# Color palette
_PRIMARY = (20, 50, 100)
_SECONDARY = (60, 60, 60)
_ACCENT = (41, 128, 185)
_LIGHT_BG = (245, 247, 250)
_WHITE = (255, 255, 255)


class B3ReportPDF(FPDF):
    """Custom PDF with professional styling for B3 reports."""

    def __init__(self, report_date: datetime):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_date = report_date
        self.set_auto_page_break(auto=True, margin=20)
        self._is_cover = False

    def header(self):
        if self._is_cover:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_ACCENT)
        self.cell(0, 6, "B3 DATA PLATFORM", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, self.report_date.strftime("%d/%m/%Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self._is_cover:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(160, 160, 160)
        self.cell(0, 8, f"{self.page_no()}", align="C")

    def add_cover(self):
        """Professional cover page."""
        self._is_cover = True
        self.add_page()

        # Top accent bar
        self.set_fill_color(*_PRIMARY)
        self.rect(0, 0, 210, 6, "F")

        # Main title block
        self.ln(55)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(*_PRIMARY)
        self.cell(0, 14, "RELATORIO", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 32)
        self.cell(0, 14, "ANALITICO", align="C", new_x="LMARGIN", new_y="NEXT")

        # Accent line
        self.ln(4)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(1)
        self.line(70, self.get_y(), 140, self.get_y())
        self.ln(10)

        # Subtitle
        self.set_font("Helvetica", "", 14)
        self.set_text_color(*_SECONDARY)
        self.cell(0, 8, "B3 - Bolsa de Valores do Brasil", align="C", new_x="LMARGIN", new_y="NEXT")

        # Date info
        self.ln(35)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, f"Data: {self.report_date.strftime('%d/%m/%Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, f"Hora: {self.report_date.strftime('%H:%M')} UTC", align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom accent bar
        self.set_fill_color(*_PRIMARY)
        self.rect(0, 285, 210, 12, "F")

        self._is_cover = False

    def add_section(self, title: str, description: str = ""):
        """Add section with styled title."""
        self.add_page()
        # Section accent
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 10, self.get_y() + 12)

        self.set_x(14)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*_PRIMARY)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        if description:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(100, 100, 100)
            self.multi_cell(0, 4.5, description)
            self.ln(4)

    def add_chart(self, image_path: str):
        """Embed a chart image with padding."""
        if not image_path or not Path(image_path).exists():
            return
        available_width = self.w - self.l_margin - self.r_margin
        self.image(image_path, w=available_width)
        self.ln(4)

    def add_summary_table(self, summary_df: pl.DataFrame):
        """Portfolio summary table with alternating row colors."""
        col_widths = [22, 26, 26, 24, 28, 28, 26]
        headers = ["Ticker", "Inicio", "Fim", "Retorno", "Vol. Media", "Volat.", "Max Preco"]

        # Header row
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*_PRIMARY)
        self.set_text_color(*_WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=0, align="C", fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 8)
        for row_idx, row in enumerate(summary_df.head(12).iter_rows(named=True)):
            if row_idx % 2 == 0:
                self.set_fill_color(*_LIGHT_BG)
            else:
                self.set_fill_color(*_WHITE)
            self.set_text_color(40, 40, 40)

            ticker = row.get("ticker", "").replace(".SA", "")
            first_date = row.get("first_date")
            last_date = row.get("last_date")
            total_return = row.get("total_return", 0) or 0
            avg_vol = row.get("avg_daily_volume", 0) or 0
            avg_volatility = row.get("avg_volatility", 0) or 0
            period_high = row.get("period_high", 0) or 0

            first_str = first_date.strftime("%d/%m/%y") if first_date else "-"
            last_str = last_date.strftime("%d/%m/%y") if last_date else "-"

            # Color code returns
            ret_str = f"{total_return*100:.2f}%"

            self.cell(col_widths[0], 6, ticker, border=0, align="C", fill=True)
            self.cell(col_widths[1], 6, first_str, border=0, align="C", fill=True)
            self.cell(col_widths[2], 6, last_str, border=0, align="C", fill=True)

            # Return with color
            if total_return >= 0:
                self.set_text_color(34, 139, 34)
            else:
                self.set_text_color(220, 50, 50)
            self.cell(col_widths[3], 6, ret_str, border=0, align="C", fill=True)
            self.set_text_color(40, 40, 40)

            self.cell(col_widths[4], 6, f"{avg_vol/1e6:.1f}M", border=0, align="C", fill=True)
            self.cell(col_widths[5], 6, f"{avg_volatility*100:.1f}%", border=0, align="C", fill=True)
            self.cell(col_widths[6], 6, f"R${period_high:.2f}", border=0, align="C", fill=True)
            self.ln()

        # Bottom line
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 190, self.get_y())


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
    Charts replicate the notebooks visualizations.

    Output: report_YYMMDD_HHMM.pdf
    """
    report_date = report_date or datetime.now(timezone.utc)
    output_dir = output_dir or OUTPUTS_PATH
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"report_{report_date.strftime('%y%m%d_%H%M')}.pdf"
    output_path = output_dir / filename

    logger.info("Generating PDF report", extra={"output": str(output_path)})

    pdf = B3ReportPDF(report_date=report_date)
    pdf.alias_nb_pages()

    # 1. Cover
    pdf.add_cover()

    # 2. Portfolio Summary
    if not portfolio_summary.is_empty():
        pdf.add_section(
            "Resumo do Portfolio",
            "Visao geral dos ativos monitorados no periodo, incluindo retorno acumulado, "
            "volume medio e volatilidade anualizada.",
        )
        pdf.add_summary_table(portfolio_summary)

    # 3. Cumulative Return (notebook 03 cell 5)
    if not daily_metrics.is_empty():
        pdf.add_section(
            "Retorno Acumulado",
            "Evolucao do retorno acumulado dos principais ativos ao longo do periodo.",
        )
        pdf.add_chart(chart_cumulative_return(daily_metrics))

    # 4. Volatility 20d (notebook 03 cell 6)
    if not daily_metrics.is_empty():
        pdf.add_section(
            "Volatilidade Anualizada",
            "Volatilidade com janela movel de 20 dias para os principais ativos. "
            "Valores mais altos indicam maior risco.",
        )
        pdf.add_chart(chart_volatility_20d(daily_metrics))

    # 5. Risk vs Return (notebook 03 cell 8)
    if not portfolio_summary.is_empty():
        pdf.add_section(
            "Risco x Retorno",
            "Relacao entre volatilidade media (risco) e retorno total de cada ativo no periodo.",
        )
        path = chart_risk_vs_return(portfolio_summary)
        if path:
            pdf.add_chart(path)

    # 6. Monthly Heatmap (notebook 03 cell 10)
    if not monthly_returns.is_empty():
        pdf.add_section(
            "Retornos Mensais",
            "Mapa de calor dos retornos mensais (%) por ativo. "
            "Verde indica retorno positivo, vermelho negativo.",
        )
        path = chart_monthly_heatmap(monthly_returns)
        if path:
            pdf.add_chart(path)

    # 7. Correlation Matrix (notebook 04 cell 4)
    if not daily_metrics.is_empty():
        pdf.add_section(
            "Matriz de Correlacao",
            "Correlacao de Pearson entre os retornos diarios dos ativos.",
        )
        pdf.add_chart(chart_correlation_matrix(daily_metrics))

    # 8. Bollinger Bands (notebook 04 cell 6)
    if not daily_metrics.is_empty():
        # Use the first available ticker from TOP5
        available = daily_metrics.filter(pl.col("ticker").is_in(TOP5))["ticker"].unique().to_list()
        if available:
            pdf.add_section(
                f"Bandas de Bollinger - {available[0].replace('.SA', '')}",
                "Preco de fechamento com media movel de 20 dias e bandas de 2 desvios padrao.",
            )
            pdf.add_chart(chart_bollinger_bands(daily_metrics, ticker=available[0]))

    # 9. Portfolio Backtest (notebook 04 cell 8)
    if not daily_metrics.is_empty():
        pdf.add_section(
            "Backtest - Portfolio Ponderado",
            "Simulacao de retorno acumulado de um portfolio com pesos iguais entre todos os ativos.",
        )
        path = chart_portfolio_backtest(daily_metrics)
        if path:
            pdf.add_chart(path)

    # Save PDF
    pdf.output(str(output_path))
    logger.info("PDF report generated", extra={"path": str(output_path), "pages": pdf.page_no()})

    # Cleanup temp chart files
    for f in glob.glob(tempfile.gettempdir() + "/tmp*.png"):
        try:
            os.unlink(f)
        except OSError:
            pass

    return output_path
