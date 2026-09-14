"""Report generation (ROADMAP.md chapter 41).

Turns a backtest result plus its chapter 40 performance report into
HTML, CSV and JSON reports. Standard library only; no report may claim
future profitability, and every report labels its evidence level
(chapters 1 and 43): a single backtest run is always an *observed
result*, never statistical evidence.

Research and qualification reports (with experiment identifiers,
chapter 52) and paper-trading reports (chapter 57) reuse this module
once those layers exist; they are not implemented yet.
"""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from crypto_trading_lab import __version__
from crypto_trading_lab.backtesting.engine import BacktestResult
from crypto_trading_lab.backtesting.metrics import DISCLAIMER, PerformanceReport

__all__ = [
    "EVIDENCE_LEVEL",
    "BacktestReportData",
    "build_backtest_report",
    "render_json",
    "render_csv",
    "render_html",
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

    return BacktestReportData(
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
    for key, value in data.parameters.items():
        lines.append(f"parameter,{key},{value}")
    for key, value in data.metrics.items():
        lines.append(f"metric,{key},{value}")
    for key, value in data.benchmark.items():
        lines.append(f"benchmark,{key},{value}")
    for warning in data.warnings:
        lines.append(f"warning,,\"{warning}\"")
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
    parts.append("</table></body></html>")
    return "\n".join(parts) + "\n"
