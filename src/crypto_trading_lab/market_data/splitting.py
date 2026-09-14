"""Chronological data splitting (ROADMAP.md chapter 38).

Financial time series are divided **chronologically** into training,
validation and out-of-sample test periods. Splitting never shuffles:
the out-of-sample period always comes last and stays isolated from
strategy development. Every split records the exact timestamp
boundaries, and reusing the test period is recorded and warned about
(38.5) — a test set you keep peeking at slowly becomes training data.

Purged/embargoed cross-validation (38.8) is a research capability
specified for chapter 49.4 and is not implemented here.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from crypto_trading_lab.domain.models import Candle

__all__ = [
    "PeriodKind",
    "PeriodSlice",
    "DatasetSplit",
    "split_candles",
]


class PeriodKind(enum.Enum):
    TRAINING = "training"
    VALIDATION = "validation"
    OUT_OF_SAMPLE = "out_of_sample"


@dataclass(frozen=True)
class PeriodSlice:
    """One chronological period, with its exact recorded boundaries.

    ``candles`` may start with a warm-up prefix borrowed from the
    previous period (38.1 "respect indicator warm-up periods"); the
    true period always begins after that prefix, and the recorded
    ``first_open``/``last_close`` exclude it.
    """

    kind: PeriodKind
    candles: tuple[Candle, ...]
    warmup: tuple[Candle, ...] = ()

    @property
    def first_open(self) -> str:
        return self.candles[len(self.warmup)].open_time.isoformat()

    @property
    def last_close(self) -> str:
        return self.candles[-1].close_time.isoformat()


@dataclass
class DatasetSplit:
    """A three-period chronological split with an evaluation log."""

    training: PeriodSlice
    validation: PeriodSlice
    out_of_sample: PeriodSlice
    fractions: tuple[str, str, str]
    # 38.3/38.5: recording repeated use of the test period.
    evaluation_log: list[PeriodKind] = field(default_factory=list)

    def boundaries(self) -> dict[str, str]:
        """Exact timestamp boundaries of every period (38.1, 38.6)."""
        out: dict[str, str] = {}
        for period in (self.training, self.validation, self.out_of_sample):
            out[f"{period.kind.value}_first_open"] = period.first_open
            out[f"{period.kind.value}_last_close"] = period.last_close
            out[f"{period.kind.value}_warmup_candles"] = str(
                len(period.warmup)
            )
        return out

    def record_evaluation(self, period: PeriodKind) -> str | None:
        """Log an evaluation; warn when the test set is reused.

        The out-of-sample period is the final historical evaluation
        (38.4). Evaluating it more than once is a leakage smell and
        returns a warning instead of staying silent.
        """
        self.evaluation_log.append(period)
        if period is PeriodKind.OUT_OF_SAMPLE and self.evaluation_log.count(
            PeriodKind.OUT_OF_SAMPLE
        ) > 1:
            return (
                "the out-of-sample test period has now been evaluated "
                f"{self.evaluation_log.count(PeriodKind.OUT_OF_SAMPLE)} "
                "times; repeated use turns it into part of the "
                "optimization process (38.3, 38.5)"
            )
        return None


def split_candles(
    candles: Sequence[Candle],
    train_fraction: Decimal = Decimal("0.6"),
    validation_fraction: Decimal = Decimal("0.2"),
    warmup: int = 0,
) -> DatasetSplit:
    """Split candles chronologically: training → validation → test.

    .. text:: Historical Data → Training → Validation → Out-of-Sample

    Guarantees (38.1): temporal order is preserved (input is checked),
    no observation moves backward in time, and no randomness is used.
    ``warmup`` candles are borrowed from the end of each preceding
    period so indicators can warm up without leaking the period's own
    observations into it.
    """
    if warmup < 0:
        raise ValueError("warmup must be >= 0")
    if not (0 < train_fraction < 1) or not (0 <= validation_fraction < 1):
        raise ValueError("invalid split fractions")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("out-of-sample period must not be empty")

    n = len(candles)
    if n < 10:
        raise ValueError(
            "need at least 10 candles for a three-way split "
            f"(got {n})"
        )
    # 38.1/38.5: detect non-chronological data instead of using it.
    for previous, current in zip(candles, candles[1:]):
        if current.open_time <= previous.open_time:
            raise ValueError(
                "candles are not in chronological order; refusing to "
                "split (a shuffled series leaks information)"
            )

    train_end = int(Decimal(n) * train_fraction)
    validation_end = train_end + int(Decimal(n) * validation_fraction)
    if train_end < 1 or validation_end <= train_end or validation_end >= n:
        raise ValueError("fractions leave an empty period")

    segments = (
        candles[:train_end],
        candles[train_end:validation_end],
        candles[validation_end:],
    )

    def with_warmup(kind: PeriodKind, start: int, segment) -> PeriodSlice:
        prefix = tuple(candles[max(0, start - warmup): start])
        return PeriodSlice(
            kind=kind, candles=tuple(prefix) + tuple(segment), warmup=prefix
        )

    return DatasetSplit(
        training=with_warmup(PeriodKind.TRAINING, 0, segments[0]),
        validation=with_warmup(PeriodKind.VALIDATION, train_end, segments[1]),
        out_of_sample=with_warmup(
            PeriodKind.OUT_OF_SAMPLE, validation_end, segments[2]
        ),
        fractions=(
            str(train_fraction),
            str(validation_fraction),
            str(Decimal(1) - train_fraction - validation_fraction),
        ),
    )
