"""Report generation (ROADMAP.md chapter 41).

Turns a backtest result plus its chapter 40 performance report into
HTML, CSV, JSON, and PDF reports. No report may claim future profitability,
and every report labels its evidence level (chapters 1 and 43): a single
backtest run is always an *observed result*, never statistical evidence.

Research and qualification reports (with experiment identifiers,
chapter 52) and paper-trading reports (chapter 57) reuse this module
once those layers exist; they are not implemented yet.
"""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from crypto_trading_lab import __version__
from crypto_trading_lab.backtesting.engine import BacktestResult
from crypto_trading_lab.backtesting.metrics import DISCLAIMER, PerformanceReport
from crypto_trading_lab.reporting.ethics import (
    ETHICS_WARNING,
    STANDARD_DISCLAIMERS,
    EthicalCheckResult,
    EthicsChecker,
    EthicsError,
)

__all__ = [
    "EVIDENCE_LEVEL",
    "BacktestReportData",
    "build_backtest_report",
    "audit_report_ethics",
    "EthicsError",
    "render_json",
    "render_csv",
    "render_html",
    "render_pdf",
]

#: Chapters 1 and 43: a single backtest run is descriptive at most.
EVIDENCE_LEVEL = (
    "observed result (single in-sample backtest; descriptive only, "
    "not statistical evidence)"
)


def _dataset_checksum(result: BacktestResult) -> str:
    """Stable identifier for the run's data identity (chapter 41)."""
    digest = hashlib.sha256()
    digest.update(result.dataset_period.encode("utf-8"))
    digest.update(str(result.candle_count).encode("utf-8"))
    for value in result.equity_curve:
        digest.update(str(value).encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class BacktestReportData:
    """Everything chapter 41 requires a report to contain."""

    strategy: str
    strategy_version: str
    parameters: dict[str, str]
    dataset_checksum: str
    dataset_version: str
    time_range: str
    exchange: str
    trading_pair: str
    interval: str
    initial_capital: str
    fees: str
    slippage: str
    execution_model: str
    metrics: dict[str, str]
    trades: list[dict[str, str]]
    equity_curve: list[str]
    max_drawdown: str
    max_drawdown_duration: str
    benchmark: dict[str, str]
    warnings: list[str]
    app_version: str
    generation_date: str
    evidence_level: str
    beginner_summary: str
    # -- chapter 72: honest reporting ------------------------------------
    disclaimers: list[str]
    assumptions: str
    limitations: str
    ethics_violations: list[str]
    ethics_warnings: list[str]


def build_backtest_report(
    result: BacktestResult,
    report: PerformanceReport,
    symbol: str,
    interval: str,
    exchange: str = "mock (CSV import)",
    generated_at: datetime | None = None,
) -> BacktestReportData:
    """Assemble the chapter 41 report payload from engine + metrics."""
    r, s, risk, a = (
        report.returns, report.trades, report.risk, report.activity
    )
    metrics = {
        "initial_capital": str(r.initial_capital),
        "final_equity": str(r.final_equity),
        "net_profit": str(r.net_profit),
        "gross_profit": str(r.gross_profit),
        "gross_loss": str(r.gross_loss),
        "total_return": str(r.total_return),
        "annualized_return": str(r.annualized_return),
        "annualized_is_valid": str(r.annualized_is_valid),
        "number_of_trades": str(s.number_of_trades),
        "winning_trades": str(s.winning_trades),
        "losing_trades": str(s.losing_trades),
        "win_rate": str(s.win_rate),
        "average_winning_trade": str(s.average_winning_trade),
        "average_losing_trade": str(s.average_losing_trade),
        "profit_factor": str(s.profit_factor),
        "expectancy": str(s.expectancy),
        "max_drawdown": str(risk.max_drawdown),
        "max_drawdown_duration": str(risk.max_drawdown_duration),
        "volatility": str(risk.volatility),
        "sharpe_ratio": str(risk.sharpe_ratio),
        "sharpe_is_valid": str(risk.sharpe_is_valid),
        "sortino_ratio": str(risk.sortino_ratio),
        "sortino_is_valid": str(risk.sortino_is_valid),
        "calmar_ratio": str(risk.calmar_ratio),
        "market_exposure": str(risk.market_exposure),
        "turnover": str(a.turnover),
        "number_of_orders": str(a.number_of_orders),
        "commissions_and_fees": str(a.trading_fees),
        "spread_cost": str(a.spread_cost),
        "slippage_cost": str(a.slippage_cost),
    }
    benchmark = {}
    if report.benchmark is not None:
        benchmark = {
            "name": report.benchmark.benchmark_name,
            "absolute_return": str(report.benchmark.absolute_return),
            "benchmark_return": str(report.benchmark.benchmark_return),
            "excess_return": str(report.benchmark.excess_return),
        }

    beginner_summary = (
        f"The strategy '{result.strategy_name}' was tested on "
        f"{result.candle_count} {symbol} candles ({interval}) from "
        f"{result.dataset_period}. It ended with {result.final_equity} "
        f"after starting from {result.initial_capital}, after paying "
        f"{a.trading_fees} in fees. The worst drop from a previous peak "
        f"was {risk.max_drawdown}. This is an observed result on past "
        "data only: it is not evidence that the strategy will make "
        "money in the future."
    )

    assumptions = (
        "Assumptions: signals are decided at a candle's close and filled at "
        "the next candle's open; costs are the taker fee, spread and slippage "
        "recorded above under the "
        f"{result.config_metadata.get('execution_model', 'next-open')} "
        "execution model. No market impact, partial fill, latency or exchange "
        "rejection is modelled."
    )
    limitations = (
        "Limitations: this is a single in-sample run. No out-of-sample "
        "validation, walk-forward test or market-regime analysis was "
        "performed, and no market-impact model exists, so the result is an "
        "observed result and never statistical evidence."
    )
    disclaimers = [
        disclaimer.text
        for disclaimer in EthicsChecker().generate_required_disclaimers(
            "backtest_report"
        )
    ] + [STANDARD_DISCLAIMERS["general"].text]

    data = BacktestReportData(
        strategy=result.strategy_name,
        strategy_version=result.strategy_version,
        parameters=dict(result.config_metadata),
        dataset_checksum=_dataset_checksum(result),
        dataset_version=result.dataset_version,
        time_range=result.dataset_period,
        exchange=exchange,
        trading_pair=symbol,
        interval=interval,
        initial_capital=str(result.initial_capital),
        fees=str(a.trading_fees),
        slippage=str(a.slippage_cost),
        execution_model=result.config_metadata.get("execution_model", ""),
        metrics=metrics,
        trades=[
            {
                "entry_time": t.entry_time,
                "exit_time": str(t.exit_time),
                "side": t.side,
                "quantity": str(t.quantity),
                "entry_price": str(t.entry_price),
                "exit_price": str(t.exit_price),
                "net_pnl": str(t.net_pnl),
            }
            for t in result.trades
        ],
        equity_curve=[str(v) for v in result.equity_curve],
        max_drawdown=str(risk.max_drawdown),
        max_drawdown_duration=str(risk.max_drawdown_duration),
        benchmark=benchmark,
        warnings=list(report.warnings),
        app_version=__version__,
        generation_date=(
            generated_at or datetime.now(timezone.utc)
        ).isoformat(),
        evidence_level=EVIDENCE_LEVEL,
        beginner_summary=beginner_summary,
        disclaimers=disclaimers,
        assumptions=assumptions,
        limitations=limitations,
        ethics_violations=[],
        ethics_warnings=[],
    )

    # Chapter 72: no report leaves the application without passing the
    # honesty audit. A violation (missing disclaimer, profit guarantee)
    # raises; the warnings are attached so the report can show what it did
    # not discuss.
    audit = audit_report_ethics(data)
    return replace(
        data,
        ethics_violations=list(audit.violations),
        ethics_warnings=list(audit.warnings),
    )


def audit_report_ethics(
    data: BacktestReportData, *, raise_on_violation: bool = True
) -> EthicalCheckResult:
    """Run the chapter-72 checks over every rendered report format.

    Raises :class:`EthicsError` on a violation unless
    ``raise_on_violation`` is false. Warnings are returned so the caller can
    surface them instead of hiding them.
    """
    checker = EthicsChecker()
    violations: list[str] = []
    warnings: list[str] = []
    for content in (render_html(data), render_csv(data), render_json(data)):
        result = checker.check_report(
            "backtest_report", content, {"evidence_level": data.evidence_level}
        )
        for violation in result.violations:
            if violation not in violations:
                violations.append(violation)
        for warning in result.warnings:
            if warning not in warnings:
                warnings.append(warning)

    if violations and raise_on_violation:
        raise EthicsError("; ".join(violations))

    return EthicalCheckResult(
        compliant=not violations,
        violations=violations,
        warnings=warnings,
        required_disclaimers=checker.generate_required_disclaimers(
            "backtest_report"
        ),
    )


def render_json(data: BacktestReportData) -> str:
    """Serialize the report as JSON (chapter 41: machine-readable)."""
    from dataclasses import asdict

    payload = asdict(data)
    payload["disclaimer"] = DISCLAIMER
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_csv(data: BacktestReportData) -> str:
    """Serialize the report as CSV sections of ``key,value`` rows."""
    lines = ["section,key,value"]
    lines.append(f'metadata,disclaimer,"{DISCLAIMER}"')
    lines.append(f"metadata,evidence_level,{data.evidence_level}")
    for key in (
        "strategy", "strategy_version", "dataset_checksum",
        "dataset_version", "time_range", "exchange", "trading_pair",
        "interval", "initial_capital", "fees", "slippage",
        "execution_model", "app_version", "generation_date",
    ):
        lines.append(f"metadata,{key},{getattr(data, key)}")
    lines.append(f'metadata,assumptions,"{data.assumptions}"')
    lines.append(f'metadata,limitations,"{data.limitations}"')
    for key, value in data.parameters.items():
        lines.append(f"parameter,{key},{value}")
    for key, value in data.metrics.items():
        lines.append(f"metric,{key},{value}")
    for key, value in data.benchmark.items():
        lines.append(f"benchmark,{key},{value}")
    for warning in data.warnings:
        lines.append(f"warning,,\"{warning}\"")
    for text in data.disclaimers:
        lines.append(f'disclaimer,,"{text}"')
    for warning in data.ethics_warnings:
        lines.append(f'ethics_warning,,"{warning}"')
    for violation in data.ethics_violations:
        lines.append(f'ethics_violation,,"{violation}"')
    lines.append(f'ethics,,"{ETHICS_WARNING}"')
    for i, trade in enumerate(data.trades):
        for key, value in trade.items():
            lines.append(f"trade[{i}],{key},{value}")
    for i, value in enumerate(data.equity_curve):
        lines.append(f"equity_curve,[{i}],{value}")
    return "\n".join(lines) + "\n"


def render_html(data: BacktestReportData) -> str:
    """Serialize the report as a standalone HTML document."""

    def esc(text: str) -> str:
        return html.escape(text, quote=True)

    def row(key: str, value: str) -> str:
        return f"<tr><th>{esc(key)}</th><td>{esc(value)}</td></tr>"

    parts = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8">'
        f"<title>Crypto Trading Lab report — {esc(data.strategy)}</title>"
        "</head><body>",
        f"<h1>Backtest report — {esc(data.strategy)}</h1>",
        f"<p><em>{esc(DISCLAIMER)}</em></p>",
        f"<p><strong>Evidence level:</strong> {esc(data.evidence_level)}"
        "</p>",
        f"<h2>Summary</h2><p>{esc(data.beginner_summary)}</p>",
        f"<h2>Assumptions</h2><p>{esc(data.assumptions)}</p>",
        f"<h2>Limitations</h2><p>{esc(data.limitations)}</p>",
        "<h2>Setup</h2><table>",
    ]
    for key in (
        "strategy_version", "dataset_checksum", "dataset_version",
        "time_range", "exchange", "trading_pair", "interval",
        "initial_capital", "fees", "slippage", "execution_model",
        "app_version", "generation_date",
    ):
        parts.append(row(key, getattr(data, key)))
    for key, value in data.parameters.items():
        parts.append(row(f"parameter: {key}", value))
    parts.append("</table><h2>Metrics</h2><table>")
    for key, value in data.metrics.items():
        parts.append(row(key, value))
    parts.append("</table><h2>Benchmark</h2><table>")
    for key, value in data.benchmark.items():
        parts.append(row(key, value))
    parts.append("</table><h2>Warnings</h2><ul>")
    for warning in data.warnings:
        parts.append(f"<li>{esc(warning)}</li>")
    parts.append("</ul><h2>Trades</h2><table>")
    if data.trades:
        header = "".join(f"<th>{esc(k)}</th>" for k in data.trades[0])
        parts.append(f"<tr>{header}</tr>")
        for trade in data.trades:
            cells = "".join(f"<td>{esc(v)}</td>" for v in trade.values())
            parts.append(f"<tr>{cells}</tr>")
    else:
        parts.append("<tr><td>No trades.</td></tr>")
    parts.append("</table><h2>Disclaimers</h2><ul>")
    for text in data.disclaimers:
        parts.append(f"<li>{esc(text)}</li>")
    parts.append("</ul>")
    if data.ethics_violations or data.ethics_warnings:
        parts.append("<h2>Ethics check</h2><ul>")
        for violation in data.ethics_violations:
            parts.append(
                f"<li><strong>violation:</strong> {esc(violation)}</li>"
            )
        for warning in data.ethics_warnings:
            parts.append(f"<li>warning: {esc(warning)}</li>")
        parts.append("</ul>")
    parts.append(f"<p><em>{esc(ETHICS_WARNING)}</em></p>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def render_pdf(data: BacktestReportData) -> bytes:
    """Serialize the report as a one-page PDF summary (chapter 41).

    Returns the raw PDF bytes. The structured formats (HTML, JSON, CSV)
    carry the full disclaimer set; this summary repeats the assumptions, the
    limitations and the ethics warning. Requires the optional ``pypdf``
    package.

    Regression: this used ``PdfWriter._addObject`` / ``_writeObject`` /
    ``.stream`` — private names that pypdf 5 removed — so PDF export raised
    ``AttributeError`` instead of returning a document.
    """
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources

    commands: list[str] = []

    def add_line(text: str, y_pos: float, font_size: int = 12) -> None:
        # Escape the PDF string delimiters: a ')' in a strategy name would
        # otherwise close the text object early.
        safe = (
            text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        commands.append(f"BT /F1 {font_size} Tf 72 {y_pos} Td ({safe}) Tj ET")

    y = 750
    add_line(f"Backtest report - {data.strategy}", 770, 16)
    y -= 30
    add_line(f"Strategy: {data.strategy} (v{data.strategy_version})", y)
    y -= 15
    add_line(f"Trading pair: {data.trading_pair}", y)
    y -= 15
    add_line(f"Time range: {data.time_range}", y)
    y -= 15
    add_line(f"Initial capital: {data.initial_capital}", y)
    y -= 25
    add_line("Metrics:", y, 14)
    y -= 15
    for key, value in list(data.metrics.items())[:10]:
        add_line(f"  {key}: {value}", y)
        y -= 12
    add_line(f"Max drawdown: {data.max_drawdown}", y)
    y -= 15
    add_line(f"Sharpe ratio: {data.metrics.get('sharpe_ratio', 'N/A')}", y)
    y -= 25
    add_line(f"Evidence level: {data.evidence_level}", y, 8)
    y -= 12
    add_line(f"Assumptions: {data.assumptions[:110]}", y, 8)
    y -= 12
    add_line(f"Limitations: {data.limitations[:110]}", y, 8)
    y -= 12
    add_line(ETHICS_WARNING[:110], y, 8)

    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("latin-1", "replace"))
    page[NameObject("/Contents")] = writer._add_object(stream)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
