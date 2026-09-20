# Crypto Trading Lab — contributor shortcuts
#
# Everything here uses Debian system packages: no virtualenv, no pip.
# Run `make` or `make help` to list the targets.

PYTHON ?= python3
SOURCES := $(shell find src -name '*.py' -not -path '*/__pycache__/*')

.PHONY: help test run banner translations clean

help: ## Show this help
	@echo "Crypto Trading Lab — available targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

test: ## Run the full offline test suite (baseline: 522 passed, 2 skipped)
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest tests/ -q

run: ## Launch the application
	PYTHONPATH=src $(PYTHON) -m crypto_trading_lab

banner: ## Regenerate the contributor banner GIF (needs python3-pil, python3-numpy)
	$(PYTHON) tools/make_banner_gif.py --preview

translations: ## Refresh and compile the Spanish translation
	pylupdate6 $(SOURCES) -ts src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts
	lrelease src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts

clean: ## Remove local caches (__pycache__, .pytest_cache)
	find . -path ./external -prune -o -name '__pycache__' -type d -print0 \
		| xargs -0 rm -rf
	rm -rf .pytest_cache
