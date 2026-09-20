#!/usr/bin/env python3
"""Setup script for crypto-trading-lab (Chapter 15/16)."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crypto-trading-lab",
    version="0.0.0.dev0",
    author="Crypto Trading Lab",
    author_email="support@crypto-trading-lab",
    description="Educational platform for cryptocurrency markets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wachin/crypto-trading-lab",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Education",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    license="GPL-3.0",
    license_files=("LICENSE",),
    keywords=[
        "cryptocurrency",
        "backtesting",
        "quantitative-research",
        "trading",
        "education",
    ],
    python_requires=">=3.11",
    install_requires=[
        "PyQt6>=6.9",
        "SQLAlchemy>=2.0",
    ],
    extras_require={
        "ccxt": ["ccxt>=4.0"],
        "dev": [
            "pytest>=8.0",
            "pytest-qt>=4.4",
            "hypothesis>=6.130",
            "typeguard>=4.4",
        ],
    },
    entry_points={
        "console_scripts": [
            "crypto-trading-lab=crypto_trading_lab.ui.main_window.window:run",
        ],
    },
    include_package_data=True,
    package_data={
        "crypto_trading_lab": [
            "i18n/translations/*.qm",
            "i18n/translations/*.ts",
        ],
    },
)
