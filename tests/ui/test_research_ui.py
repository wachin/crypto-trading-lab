"""Tests for Research UI components."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")


def test_research_notebook_import():
    """Test research notebook can be imported."""
    from crypto_trading_lab.ui.research import notebook
    assert hasattr(notebook, "NotebookEntry")
    assert hasattr(notebook, "NotebookEditor")
    assert hasattr(notebook, "create_notebook_entry")


def test_research_assistant_import():
    """Test research assistant can be imported."""
    from crypto_trading_lab.ui.research import assistant
    assert hasattr(assistant, "ResearchAssistantDialog")
    assert hasattr(assistant, "research_assistant")


def test_strategy_builder_import():
    """Test strategy builder can be imported."""
    from crypto_trading_lab.ui.strategy_builder import StrategyBuilderDialog
    assert StrategyBuilderDialog is not None
