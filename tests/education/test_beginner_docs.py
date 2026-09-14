"""Documentation tests (ROADMAP.md chapter 14.8).

Verify that required beginner guides exist, contain the mandated
content, and that the glossary defines every required term.
"""

from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs" / "en" / "beginners"

REQUIRED_TERMS = (
    "cryptocurrency",
    "Bitcoin",
    "exchange",
    "trading pair",
    "candle",
    "volume",
    "order",
    "fee",
    "slippage",
    "volatility",
    "strategy",
    "backtesting",
    "paper trading",
    "risk",
    "drawdown",
)


def test_start_here_guide_exists():
    assert (DOCS / "00-start-here.md").is_file()


def test_start_here_explains_what_it_is_and_is_not():
    text = (DOCS / "00-start-here.md").read_text(encoding="utf-8")
    assert "## What Crypto Trading Lab is" in text
    assert "## What Crypto Trading Lab is not" in text


def test_start_here_states_no_guarantee():
    text = (DOCS / "00-start-here.md").read_text(encoding="utf-8").lower()
    # Collapse newlines so phrases wrapped across lines still match.
    flat = " ".join(text.split())
    assert "guarantee profits" in flat
    assert "not a money-making machine" in flat


def test_start_here_states_paper_trading_default():
    text = (DOCS / "00-start-here.md").read_text(encoding="utf-8")
    assert "Paper Trading" in text
    assert "disabled" in text.lower()


def test_start_here_explains_where_to_begin():
    text = (DOCS / "00-start-here.md").read_text(encoding="utf-8")
    assert "Learning Center" in text


def test_start_here_warns_against_real_money():
    text = (DOCS / "00-start-here.md").read_text(encoding="utf-8").lower()
    assert "real money" in text
    assert "money you need to live" in text
    assert "borrowed money" in text  # never trade with loans
    assert "farmer" in text  # the farmer's truth frames the doc


def test_glossary_exists():
    assert (DOCS / "glossary.md").is_file()


def test_glossary_defines_all_required_terms():
    text = (DOCS / "glossary.md").read_text(encoding="utf-8").lower()
    for term in REQUIRED_TERMS:
        assert term.lower() in text, f"glossary missing term: {term}"


def test_glossary_entries_have_simple_words_and_warnings():
    text = (DOCS / "glossary.md").read_text(encoding="utf-8")
    # Every beginner entry explains in plain language...
    assert text.count("In simple words") >= 15
    # ...and warns where it matters.
    assert text.count("Warning:") >= 5


def test_indicators_guide_exists_and_covers_all():
    path = DOCS / "indicators-explained.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for name in ("SMA", "EMA", "RSI", "Bollinger", "ATR", "ROC"):
        assert name in text
    # Each indicator section must have the mandated subsections.
    for section in (
        "What it measures",
        "Plain words",
        "Common values",
        "Typical misuse",
        "Limits",
    ):
        assert section in text


def test_indicators_guide_warns_no_prediction():
    text = (DOCS / "indicators-explained.md").read_text(encoding="utf-8").lower()
    assert "cannot guarantee" in text or "no combination of them" in text
    assert "lens, not a crystal ball" in text
