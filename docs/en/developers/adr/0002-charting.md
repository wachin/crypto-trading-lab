# ADR-0002: Charting Library

## Status
Accepted

## Context
We need to display candlestick charts for market analysis. The library must be:
* Performant for real-time updates
* Integrated with Qt
* Free/open source

## Decision
We use **pyqtgraph** for all charting.

## Consequences

### Positive
* Fast rendering (OpenGL-based)
* Native Qt integration
* Active development
* No additional licensing concerns

### Negative
* Requires Qt to be installed
* Limited mobile support (not a requirement)

### Alternatives Considered
* **matplotlib**: Slower for real-time, less Qt-integrated
* **Plotly**: Requires web view, adds complexity
