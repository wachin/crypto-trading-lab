# Architecture Proposal

## Overview

Crypto Trading Lab is a desktop application for cryptocurrency research, simulation, and analysis. It prioritizes capital preservation, research honesty, and educational clarity.

## Core Principles

1.  **Capital protection first** - Risk manager and safety gates operate independently from strategies.
2.  **Research honesty** - Never promise profits; clearly label evidence levels.
3.  **Separation of concerns** - Research, execution, and risk are separate responsibilities.
4.  **Educational focus** - Every feature includes beginner explanations.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (Qt)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Charts  │ │ Backtest │ │   Paper  │ │  Monitor │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Services                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Risk Mgr  │ │ Safety Gates│ │ Kill Switch │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Backtest   │ │  Paper      │ │  Portfolio  │           │
│  │   Engine    │ │  Trading    │ │  Metrics    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Market Data│ │  SQLite     │ │  XDG Config │           │
│  │  Importer   │ │  Database   │ │             │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### User Interface (UI)
* PyQt6 desktop application
* Learning Center for beginners
* Chart display via pyqtgraph
* Environment indicator (always visible)

### Core Services
* **Risk Manager**: Enforces position and loss limits
* **Safety Gates**: Pre-trade protection for real orders
* **Kill Switch**: Emergency stop mechanism
* **Backtest Engine**: Historical strategy evaluation
* **Paper Trading**: Simulated live trading

### Data Layer
* **Market Data**: CSV import and exchange adapters
* **SQLite**: Persistent storage for candles and results
* **XDG**: Standard configuration directories

## Technology Choices

* **Language**: Python 3.13+
* **UI Framework**: PyQt6
* **Charting**: pyqtgraph
* **Database**: SQLite (via SQLAlchemy)
* **Packaging**: Debian packages
* **Internationalization**: Qt Linguist

## Data Flow

1.  **Data Ingestion**: CSV or exchange adapter loads market data
2.  **Storage**: Data stored in SQLite with UTC timestamps
3.  **Strategy**: Signal generator processes candles
4.  **Risk**: Risk manager validates proposed orders
5.  **Execution**: Backtest engine or paper trading simulates fills
6.  **Results**: Metrics computed and stored

## Security

* Credentials stored via system keyring
* No raw API keys in configuration files
* All API calls logged with sensitive data redacted
* Safety gates enforce capital protection even during errors

## Extensibility

* Strategy interface allows custom implementations
* Exchange adapter interface supports additional venues
* Research tier (AFML) can be extended without breaking core
* Translation system allows language additions

## Limitations

* Not financial advice
* Does not guarantee profits
* Paper trading does not reproduce every real condition
* Backtesting requires careful assumption validation
