# ADR-0003: Qt and Asyncio Concurrency

## Status
Accepted

## Context
The application must:
* Run a responsive Qt GUI
* Handle async network requests (exchange APIs)
* Avoid blocking the UI thread

## Decision
We use **Qt's event loop** as the primary concurrency model, with **asyncio** for network operations. Async code runs in separate threads via `QThread` or `QRunnable`.

## Consequences

### Positive
* UI remains responsive during network calls
* Clear separation between UI and business logic
* Standard Python async patterns available

### Negative
* Requires careful thread management
* Cannot use Qt objects from worker threads

### Alternatives Considered
* **Pure asyncio with PyQt5**: Qt event loop integration was more complex
* **Multiprocessing**: Too heavy for this use case
