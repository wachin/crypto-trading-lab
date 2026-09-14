"""Technical indicators (ROADMAP.md chapter 31).

Every indicator uses a common interface, validates its parameters,
documents its formula and warm-up period, avoids look-ahead bias, and
supports batch calculation. Results are aligned with the input: index
``i`` uses only candles up to and including ``i``.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from crypto_trading_lab.domain.models import Candle

__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorError",
    "SMA",
    "EMA",
    "RSI",
    "BollingerBands",
    "ATR",
    "ROC",
]


class IndicatorError(ValueError):
    """Invalid indicator configuration or input."""


@dataclass(frozen=True)
class IndicatorResult:
    """One indicator run: values aligned with the input candles.

    ``values[i]`` is the indicator value after candle ``i``, or ``None``
    during the warm-up period.
    """

    name: str
    values: tuple[Decimal | None, ...]

    @property
    def warmup_length(self) -> int:
        """How many initial values are ``None`` (parameter-dependent)."""
        for index, value in enumerate(self.values):
            if value is not None:
                return index
        return len(self.values)


class Indicator(abc.ABC):
    """Common indicator interface (chapter 31)."""

    #: Human-readable formula for docs/UI (chapter 31).
    formula: str = ""

    @abc.abstractmethod
    def warmup(self) -> int:
        """Number of candles needed before the first value."""

    @abc.abstractmethod
    def validate(self) -> None:
        """Reject invalid parameters (e.g. period < 1)."""

    @abc.abstractmethod
    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        """Batch calculation over ordered candles (no look-ahead)."""

    # -- shared input guard ------------------------------------------------

    @staticmethod
    def _require_ordered(candles: Sequence[Candle]) -> None:
        previous = None
        for candle in candles:
            if previous is not None and candle.open_time <= previous:
                raise IndicatorError(
                    "candles must be chronological and unique"
                )
            previous = candle.open_time


class SMA(Indicator):
    """Simple Moving Average of the close price.

    Formula: SMA(n) at time t = (C[t-n+1] + ... + C[t]) / n.
    Warm-up: the first ``n-1`` candles produce ``None``.
    """

    def __init__(self, period: int = 20) -> None:
        self.period = period
        self.validate()

    formula = "SMA(n) = (C1 + C2 + ... + Cn) / n over the last n closes"

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError(
                f"SMA period must be a positive integer, got {self.period!r}"
            )

    def warmup(self) -> int:
        return self.period - 1

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        values: list[Decimal | None] = [None] * len(candles)
        if len(candles) < self.period:
            return IndicatorResult("SMA", tuple(values))
        window_sum = Decimal(0)
        for index, candle in enumerate(candles):
            window_sum += candle.close
            if index >= self.period:
                window_sum -= candles[index - self.period].close
            if index >= self.period - 1:
                values[index] = window_sum / Decimal(self.period)
        return IndicatorResult("SMA", tuple(values))


class EMA(Indicator):
    """Exponential Moving Average of the close price.

    Formula: EMA[0] = SMA(n) of the first n closes; afterwards
    EMA[t] = alpha * C[t] + (1 - alpha) * EMA[t-1] with
    alpha = 2 / (n + 1). Warm-up: first ``n-1`` candles are ``None``.
    """

    def __init__(self, period: int = 20) -> None:
        self.period = period
        self.validate()

    formula = (
        "EMA[t] = alpha * C[t] + (1 - alpha) * EMA[t-1], "
        "alpha = 2 / (n + 1); seeded with SMA(n)"
    )

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError(
                f"EMA period must be a positive integer, got {self.period!r}"
            )

    def warmup(self) -> int:
        return self.period - 1

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        values: list[Decimal | None] = [None] * len(candles)
        n = self.period
        if len(candles) < n:
            return IndicatorResult("EMA", tuple(values))
        alpha = Decimal(2) / Decimal(n + 1)
        # Seed with the SMA of the first n closes.
        seed = sum(candles[i].close for i in range(n)) / Decimal(n)
        values[n - 1] = seed
        ema = seed
        for index in range(n, len(candles)):
            ema = alpha * candles[index].close + (Decimal(1) - alpha) * ema
            values[index] = ema
        return IndicatorResult("EMA", tuple(values))


class RSI(Indicator):
    """Relative Strength Index (Wilder).

    Formula: RSI = 100 - 100 / (1 + RS), where RS = average gain /
    average loss over the period (Wilder smoothing). Warm-up: first
    ``period`` candles are ``None``; the first value appears at index
    ``period``.
    """

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self.validate()

    formula = (
        "RSI = 100 - 100 / (1 + RS); RS = avg gain / avg loss "
        "(Wilder smoothing over n periods)"
    )

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError(
                f"RSI period must be a positive integer, got {self.period!r}"
            )

    def warmup(self) -> int:
        return self.period

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        values: list[Decimal | None] = [None] * len(candles)
        n = self.period
        if len(candles) <= n:
            return IndicatorResult("RSI", tuple(values))
        gains: list[Decimal] = []
        losses: list[Decimal] = []
        for index in range(1, n + 1):
            change = candles[index].close - candles[index - 1].close
            gains.append(max(change, Decimal(0)))
            losses.append(max(-change, Decimal(0)))
        avg_gain = sum(gains) / Decimal(n)
        avg_loss = sum(losses) / Decimal(n)
        values[n] = self._rsi_from(avg_gain, avg_loss)
        for index in range(n + 1, len(candles)):
            change = candles[index].close - candles[index - 1].close
            gain = max(change, Decimal(0))
            loss = max(-change, Decimal(0))
            avg_gain = (avg_gain * Decimal(n - 1) + gain) / Decimal(n)
            avg_loss = (avg_loss * Decimal(n - 1) + loss) / Decimal(n)
            values[index] = self._rsi_from(avg_gain, avg_loss)
        return IndicatorResult("RSI", tuple(values))

    @staticmethod
    def _rsi_from(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
        if avg_loss == 0:
            return Decimal(100) if avg_gain > 0 else Decimal(50)
        rs = avg_gain / avg_loss
        return Decimal(100) - Decimal(100) / (Decimal(1) + rs)


class BollingerBands(Indicator):
    """Bollinger Bands: SMA center ± k * rolling standard deviation.

    Warm-up: first ``period - 1`` candles are ``None`` for all three
    bands.
    """

    def __init__(self, period: int = 20, k: int | float = 2) -> None:
        self.period = period
        self.k = k
        self.validate()

    formula = "middle = SMA(n); upper/lower = middle ± k * stdev(n)"

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError("Bollinger period must be a positive integer")
        if not (isinstance(self.k, (int, float)) and self.k > 0):
            raise IndicatorError("Bollinger k must be a positive number")

    def warmup(self) -> int:
        return self.period - 1

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        n = self.period
        values: list[Decimal | None] = [None] * len(candles)
        if len(candles) < n:
            return IndicatorResult("BB", tuple(values))
        k = Decimal(str(self.k))
        # Rolling sum and sum of squares (population stdev, classic
        # Bollinger definition).
        window_sum = Decimal(0)
        window_sq = Decimal(0)
        for index, candle in enumerate(candles):
            window_sum += candle.close
            window_sq += candle.close * candle.close
            if index >= n:
                old = candles[index - n].close
                window_sum -= old
                window_sq -= old * old
            if index >= n - 1:
                mean = window_sum / Decimal(n)
                variance = window_sq / Decimal(n) - mean * mean
                if variance < 0:  # numeric noise guard
                    variance = Decimal(0)
                stdev = variance.sqrt()
                values[index] = mean + k * stdev  # upper by convention
        return IndicatorResult("BB", tuple(values))


class ATR(Indicator):
    """Average True Range (Wilder).

    True Range = max(high - low, |high - prev close|, |low - prev
    close|). Warm-up: first ``period`` candles are ``None``.
    """

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self.validate()

    formula = (
        "TR = max(H-L, |H-prevC|, |L-prevC|); "
        "ATR = Wilder-smoothed average of TR"
    )

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError("ATR period must be a positive integer")

    def warmup(self) -> int:
        return self.period

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        n = self.period
        values: list[Decimal | None] = [None] * len(candles)
        if len(candles) <= n:
            return IndicatorResult("ATR", tuple(values))
        trs: list[Decimal] = []
        for index in range(1, len(candles)):
            candle = candles[index]
            previous = candles[index - 1].close
            tr = max(
                candle.high - candle.low,
                abs(candle.high - previous),
                abs(candle.low - previous),
            )
            trs.append(tr)
        atr = sum(trs[:n]) / Decimal(n)
        values[n] = atr
        for index in range(n + 1, len(candles)):
            atr = (atr * Decimal(n - 1) + trs[index - 1]) / Decimal(n)
            values[index] = atr
        return IndicatorResult("ATR", tuple(values))


class ROC(Indicator):
    """Rate of Change: (close[t] / close[t-n] - 1) * 100.

    Warm-up: first ``period`` candles are ``None``.
    """

    def __init__(self, period: int = 10) -> None:
        self.period = period
        self.validate()

    formula = "ROC = (C[t] / C[t-n] - 1) * 100"

    def validate(self) -> None:
        if not isinstance(self.period, int) or self.period < 1:
            raise IndicatorError("ROC period must be a positive integer")

    def warmup(self) -> int:
        return self.period

    def compute(self, candles: Sequence[Candle]) -> IndicatorResult:
        self._require_ordered(candles)
        n = self.period
        values: list[Decimal | None] = [None] * len(candles)
        for index in range(n, len(candles)):
            past = candles[index - n].close
            if past == 0:
                continue  # undefined rate of change; stays None
            values[index] = (
                candles[index].close / past - Decimal(1)
            ) * Decimal(100)
        return IndicatorResult("ROC", tuple(values))
