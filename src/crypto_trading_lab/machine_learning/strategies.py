"""Machine learning strategies (ROADMAP.md chapter 48).

Implements ML-based strategy generation and evaluation using numpy/scipy.
Integrates with existing backtesting engine, walk-forward validation,
and statistical analysis infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Sequence, Optional

import numpy as np
from scipy import stats

from crypto_trading_lab.backtesting.engine import Strategy, Candle, OrderSide
from crypto_trading_lab.backtesting.metrics import compute_performance
from crypto_trading_lab.backtesting.engine import run_backtest, BacktestConfig, BacktestResult
from crypto_trading_lab.backtesting.statistical_analysis import (
    compute_distribution_stats,
    bootstrap_confidence_interval,
    probabilistic_sharpe_ratio,
)
from crypto_trading_lab.backtesting.robustness import walk_forward


@dataclass(frozen=True)
class MLConfig:
    """Configuration for ML strategies."""
    lookback: int = 20
    retrain_period: int = 50
    min_train_size: int = 100


class MLStrategyBase:
    """Base class for ML strategies with common utilities."""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self._model = None
        self._scaler_mean = None
        self._scaler_std = None
        self._train_count = 0
    
    def _compute_features(self, candles: Sequence[Candle], index: int) -> Optional[np.ndarray]:
        """Compute features from candle data up to index."""
        if index < self.config.lookback:
            return None
        
        # Extract price series up to index
        closes = [float(c.close) for c in candles[:index+1]]
        volumes = [float(c.volume) for c in candles[:index+1]]
        
        # Basic features
        features = []
        
        # Returns
        for lookback in [1, 5, 10, 20]:
            if len(closes) >= lookback + 1:
                ret = (closes[-1] - closes[-lookback-1]) / closes[-lookback-1]
                features.append(ret)
            else:
                features.append(0.0)
        
        # Moving averages
        for window in [5, 10, 20]:
            if len(closes) >= window:
                ma = np.mean(closes[-window:])
                features.append((closes[-1] - ma) / ma)
            else:
                features.append(0.0)
        
        # Volatility
        if len(closes) >= 20:
            returns = np.diff(closes[-20:]) / np.array(closes[-20:-1])
            features.append(np.std(returns))
        else:
            features.append(0.0)
        
        # Volume trend
        if len(volumes) >= 5:
            vol_ratio = volumes[-1] / np.mean(volumes[-5:])
            features.append(vol_ratio - 1.0)
        else:
            features.append(0.0)
        
        # RSI-like
        if len(closes) >= 14:
            gains = []
            losses = []
            for i in range(-14, 0):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(-change)
            avg_gain = np.mean(gains) if gains else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            rs = avg_gain / avg_loss if avg_loss > 0 else 0.0
            rsi = 100 - 100 / (1 + rs)
            features.append((rsi - 50) / 50)  # Normalize
        else:
            features.append(0.0)
        
        return np.array(features, dtype=np.float64)
    
    def _prepare_training_data(self, candles: Sequence[Candle], start_idx: int, end_idx: int) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data from candle sequence."""
        X = []
        y = []
        
        for i in range(start_idx, end_idx):
            features = self._compute_features(candles, i)
            if features is not None:
                X.append(features)
                # Target: next candle return direction
                if i + 1 < len(candles):
                    ret = float(candles[i+1].close - candles[i].close) / float(candles[i].close)
                    y.append(1 if ret > 0 else -1)
                else:
                    y.append(0)
        
        return np.array(X), np.array(y)
    
    def _standardize(self, X: np.ndarray, fit: bool = True) -> np.ndarray:
        """Standardize features."""
        if fit:
            self._scaler_mean = np.mean(X, axis=0)
            self._scaler_std = np.std(X, axis=0)
            self._scaler_std[self._scaler_std == 0] = 1.0
        return (X - self._scaler_mean) / self._scaler_std


class LinearRegressionStrategy(MLStrategyBase):
    """Linear regression strategy using OLS."""
    
    name = "Linear Regression ML"
    version = "1.0.0"
    
    def __init__(self, config: MLConfig = None):
        super().__init__(config or MLConfig())
        self._weights = None
        self._bias = 0.0
    
    def _train(self, X: np.ndarray, y: np.ndarray):
        """Train linear regression using OLS."""
        # Add bias term
        X_with_bias = np.column_stack([np.ones(len(X)), X])
        
        # Solve using normal equations
        XTX = X_with_bias.T @ X_with_bias
        XTy = X_with_bias.T @ y
        
        try:
            weights = np.linalg.solve(XTX, XTy)
            self._bias = weights[0]
            self._weights = weights[1:]
        except np.linalg.LinAlgError:
            # Fallback: use pseudo-inverse
            weights = np.linalg.lstsq(X_with_bias, y, rcond=None)[0]
            self._bias = weights[0]
            self._weights = weights[1:]
    
    def on_candle(self, index: int, candles: Sequence[Candle]) -> Optional[OrderSide]:
        """Make prediction using linear regression."""
        # Retrain periodically
        if self._train_count % self.config.retrain_period == 0:
            if index >= self.config.min_train_size:
                X, y = self._prepare_training_data(candles, 0, index)
                if len(X) > self.config.lookback:
                    X_std = self._standardize(X, fit=True)
                    self._train(X_std, y)
        
        self._train_count += 1
        
        # Make prediction
        features = self._compute_features(candles, index)
        if features is None or self._weights is None:
            return None
        
        features_std = self._standardize(features.reshape(1, -1), fit=False)
        prediction = features_std @ self._weights + self._bias
        
        if prediction > 0.1:
            return OrderSide.BUY
        elif prediction < -0.1:
            return OrderSide.SELL
        return None


class MeanReversionStrategy(MLStrategyBase):
    """Mean reversion strategy using statistical thresholds."""
    
    name = "Mean Reversion ML"
    version = "1.0.0"
    
    def __init__(self, config: MLConfig = None):
        super().__init__(config or MLConfig())
        self._entry_threshold = 1.5  # Z-score
        self._exit_threshold = 0.5
    
    def on_candle(self, index: int, candles: Sequence[Candle]) -> Optional[OrderSide]:
        if index < self.config.lookback:
            return None
        
        closes = [float(c.close) for c in candles[:index+1]]
        
        # Compute rolling statistics
        window = self.config.lookback
        recent = closes[-window:]
        
        mean = np.mean(recent)
        std = np.std(recent)
        
        if std == 0:
            return None
        
        current_price = float(candles[index].close)
        z_score = (current_price - mean) / std
        
        # Mean reversion: buy when significantly below mean, sell when above
        if z_score < -self._entry_threshold:
            return OrderSide.BUY
        elif z_score > self._entry_threshold:
            return OrderSide.SELL
        elif abs(z_score) < self._exit_threshold:
            return OrderSide.SELL  # Exit position
        
        return None


class TrendFollowingMLStrategy(MLStrategyBase):
    """Trend following strategy using multiple timeframe confirmation."""
    
    name = "Trend Following ML"
    version = "1.0.0"
    
    def __init__(self, config: MLConfig = None):
        super().__init__(config or MLConfig())
    
    def on_candle(self, index: int, candles: Sequence[Candle]) -> Optional[OrderSide]:
        if index < 50:
            return None
        
        closes = [float(c.close) for c in candles[:index+1]]
        
        # Multiple timeframe MAs
        ma_short = np.mean(closes[-10:])
        ma_medium = np.mean(closes[-20:])
        ma_long = np.mean(closes[-50:])
        
        current_price = float(candles[index].close)
        
        # Trend alignment
        short_above_medium = ma_short > ma_medium
        medium_above_long = ma_medium > ma_long
        
        # Price relative to MAs
        price_above_short = current_price > ma_short
        price_above_long = current_price > ma_long
        
        # Strong uptrend
        if short_above_medium and medium_above_long and price_above_short:
            return OrderSide.BUY
        
        # Strong downtrend
        if not short_above_medium and not medium_above_long and not price_above_short:
            return OrderSide.SELL
        
        return None


def evaluate_ml_strategy(
    candles: Sequence[Candle],
    strategy_factory,
    config: MLConfig = None,
    backtest_config: Optional[BacktestConfig] = None,
) -> dict:
    """
    Evaluate ML strategy using walk-forward validation (Chapter 45).
    
    Returns comprehensive evaluation metrics.
    """
    config = config or MLConfig()
    
    # Run backtest
    if isinstance(strategy_factory, type):
        strategy = strategy_factory(config)
    else:
        strategy = strategy_factory
    
    backtest_config = backtest_config or BacktestConfig()
    result = run_backtest(candles, strategy, backtest_config)
    report = compute_performance(result)
    
    # Statistical significance (Chapter 43)
    trade_returns = [float(t.net_pnl) / float(t.quantity * t.entry_price) for t in result.trades if t.net_pnl is not None]
    
    stats_results = {}
    if trade_returns:
        dist_stats = compute_distribution_stats(trade_returns)
        stats_results["distribution"] = {
            "mean": dist_stats.mean,
            "std": dist_stats.std,
            "skewness": dist_stats.skewness,
            "kurtosis": dist_stats.kurtosis,
        }
        
        # Bootstrap confidence interval
        bs = bootstrap_confidence_interval(trade_returns, lambda x: np.mean(x))
        stats_results["bootstrap_ci"] = {
            "lower": float(bs.lower),
            "upper": float(bs.upper),
        }
        
        # Probabilistic Sharpe Ratio
        if len(trade_returns) > 30:
            psr = probabilistic_sharpe_ratio(
                np.mean(trade_returns) * 252,
                np.std(trade_returns) * np.sqrt(252),
                len(trade_returns),
            )
            stats_results["psr"] = psr
    
    # Walk-forward validation (Chapter 45)
    wf_results = walk_forward(
        candles=candles,
        strategy_factory=lambda: strategy_factory(config) if isinstance(strategy_factory, type) else strategy_factory,
        backtest_config=backtest_config,
        train_window=100,
        test_window=20,
        step=10,
    )
    
    wf_returns = [float(r["test_return"]) for r in wf_results]
    wf_stats = {}
    if wf_returns:
        wf_stats = {
            "mean_test_return": np.mean(wf_returns),
            "std_test_return": np.std(wf_returns),
            "positive_windows": sum(1 for r in wf_returns if r > 0),
            "total_windows": len(wf_returns),
        }
    
    return {
        "backtest_result": {
            "total_return": float(result.return_fraction),
            "num_trades": len(result.trades),
            "sharpe_ratio": float(report.risk.sharpe_ratio) if report.risk.sharpe_ratio else None,
            "max_drawdown": float(report.risk.max_drawdown),
            "profit_factor": float(report.trades.profit_factor) if report.trades.profit_factor else None,
        },
        "statistical": stats_results,
        "walk_forward": wf_stats,
    }


#: Mandatory warning for ML strategies
ML_STRATEGY_WARNING = (
    "ML strategies are research tools, not investment advice. "
    "They use historical data to learn patterns that may not persist. "
    "Always validate with walk-forward testing (Chapter 45), "
    "robustness checks (Chapter 44), and regime analysis (Chapter 46) "
    "before any real trading decision. Past ML performance does not "
    "guarantee future results."
)


__all__ = [
    "MLConfig",
    "LinearRegressionStrategy",
    "MeanReversionStrategy", 
    "TrendFollowingMLStrategy",
    "evaluate_ml_strategy",
    "ML_STRATEGY_WARNING",
]

#: Ensemble strategies (Chapter 50).
#: Combine multiple strategies to improve robustness and stability.

class EnsembleStrategy:
    """Base class for ensemble strategies."""
    
    def __init__(self, strategies, weights=None):
        self.strategies = strategies
        if weights is None:
            # Equal weights
            self.weights = [Decimal(1) / len(strategies)] * len(strategies)
        else:
            self.weights = weights
    
    def on_candle(self, index, candles):
        """Make ensemble decision."""
        # Collect signals from all strategies
        signals = []
        for strategy in self.strategies:
            signal = strategy.on_candle(index, candles)
            if signal is not None:
                signals.append(signal)
        
        if not signals:
            return None
        
        # Weighted decision
        buy_weight = Decimal(0)
        sell_weight = Decimal(0)
        
        for i, signal in enumerate(signals):
            weight = self.weights[i] if i < len(self.weights) else Decimal(1) / len(strategies)
            if signal == OrderSide.BUY:
                buy_weight += weight
            elif signal == OrderSide.SELL:
                sell_weight += weight
        
        if buy_weight > sell_weight:
            return OrderSide.BUY
        elif sell_weight > buy_weight:
            return OrderSide.SELL
        return None

class EqualWeightEnsemble:
    """Ensemble with equal weights for all strategies."""
    
    name = "Equal Weight Ensemble"
    version = "1.0.0"
    
    def __init__(self, strategies):
        self.strategies = strategies
    
    def on_candle(self, index, candles):
        """Make ensemble decision with equal weights."""
        buy_weight = Decimal(0)
        sell_weight = Decimal(0)
        
        for strategy in self.strategies:
            signal = strategy.on_candle(index, candles)
            if signal == OrderSide.BUY:
                buy_weight += Decimal(1) / len(self.strategies)
            elif signal == OrderSide.SELL:
                sell_weight += Decimal(1) / len(self.strategies)
        
        if buy_weight > sell_weight:
            return OrderSide.BUY
        elif sell_weight > buy_weight:
            return OrderSide.SELL
        return None

def evaluate_ensemble(ensembles, candles, backtest_config=None):
    """Evaluate an ensemble of strategies."""
    from crypto_trading_lab.backtesting.engine import run_backtest
    from crypto_trading_lab.backtesting.metrics import compute_performance
    
    results = []
    for ensemble in ensembles:
        strategy = ensemble  # EnsembleStrategy or EqualWeightEnsemble
        result = run_backtest(candles, strategy, backtest_config)
        performance = compute_performance(result)
        results.append({
            "strategy_name": strategy.name,
            "return_fraction": result.return_fraction,
            "num_trades": len(result.trades),
            "sharpe_ratio": report.risk.sharpe_ratio if report.risk.sharpe_ratio else None,
            "max_drawdown": report.risk.max_drawdown,
        }
    )
    return results

ML_ENSEMBLE_WARNING = """
ML Ensembles are research tools that combine multiple strategies.
They must be validated with walk-forward testing (Chapter 45)
and statistical analysis (Chapter 43) before any real trading decision.
Ensemble methods diversify risk but do not guarantee future performance.
"""

__all__ = [
    "EnsembleStrategy",
    "EqualWeightEnsemble",
    "evaluate_ensemble",
    "ML_STRATEGY_WARNING",
]


