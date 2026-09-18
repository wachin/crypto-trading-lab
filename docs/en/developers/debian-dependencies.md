# Debian Dependencies

This document lists all Debian packages required to build and run Crypto Trading Lab.

## System packages (Debian 13/trixie)

```bash
sudo apt update
sudo apt install python3 python3-pip python3-dev python3-venv \
    python3-pyqt6 python3-pyqtgraph python3-sqlalchemy python3-platformdirs \
    python3-pytest python3-pypdf \
    pyqt6-dev-tools python3-lxml
```

## Verification

```bash
python3 --version            # ≥ 3.11 expected
python3 -c "import pyqtgraph, sqlalchemy, platformdirs, pypdf; print('deps OK')"
```

## Development tools

```bash
sudo apt install python3-pytest python3-pytest-qt python3-hypothesis python3-typeguard
```

# Debian Package Installation

This application is available as a Debian package on Debian 13 (trixie).

## Installation

```bash
sudo apt update
sudo apt install crypto-trading-lab
```

## Verification

```bash
crypto-trading-lab --version
```

## Development

For development purposes, you can install from source:

```bash
sudo apt install python3 python3-pip python3-dev python3-virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
