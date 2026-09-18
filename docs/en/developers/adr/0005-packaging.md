# ADR-0005: Packaging Backend

## Status
Accepted

## Context
The application must be:
* Easy to install on Debian
* Distributable via system package manager
* Not require manual Python setup

## Decision
We use **native Debian packages** (`.deb`). The build process compiles Python source and creates system packages.

## Consequences

### Positive
* Integration with system package manager
* Automatic dependency resolution
* Familiar to Debian users

### Negative
* Requires build infrastructure
* Slower release cycle than Python packages

### Alternatives Considered
* **PyPI wheel**: Would require Python setup
* **AppImage**: Self-contained but bypasses package manager
* **Flatpak**: Not available on all systems
