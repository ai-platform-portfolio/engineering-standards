PYTHON ?= python3
RECONCILE = $(PYTHON) scripts/reconcile.py

.PHONY: help plan install verify signal-plan signal-install signal-verify test

help:
	@echo 'make plan           Show proposed shared guidance changes'
	@echo 'make install        Review and apply shared guidance'
	@echo 'make verify         Check installed shared guidance for drift'
	@echo 'make signal-plan    Show optional Signal changes'
	@echo 'make signal-install Review and install optional Signal'
	@echo 'make signal-verify  Check optional Signal for drift'
	@echo 'make portfolio-plan / portfolio-install / portfolio-verify  Optional personal architecture guidance'
	@echo 'make test           Run reconciliation tests'

plan:
	@$(RECONCILE) plan shared

install:
	@$(RECONCILE) apply shared

verify:
	@$(RECONCILE) verify shared

signal-plan:
	@$(RECONCILE) plan signal

signal-install:
	@$(RECONCILE) apply signal

signal-verify:
	@$(RECONCILE) verify signal

.PHONY: portfolio-plan portfolio-install portfolio-verify
portfolio-plan:
	@$(RECONCILE) plan portfolio

portfolio-install:
	@$(RECONCILE) apply portfolio

portfolio-verify:
	@$(RECONCILE) verify portfolio

test:
	@$(PYTHON) -m unittest discover -s tests -v

.PHONY: tools check
tools:
	uv sync --frozen --python 3.12
	npm ci --ignore-scripts

check:
	.venv/bin/ruff check checks
	.venv/bin/ruff format --check checks
	.venv/bin/mypy checks
	$(MAKE) test
