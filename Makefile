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
	@$(PYTHON) -m unittest discover -s tests -p test_reconcile.py -v
	@$(PYTHON) -m unittest discover -s tests -p test_linear_hook.py -v
	@$(PYTHON) -m unittest discover -s tests -p test_linear_workspace.py -v

.PHONY: hooks-install hooks-refresh hooks-status hooks-uninstall
WORKSPACE ?= $(error Set WORKSPACE to your repository directory)
HOOK_POLICY ?= policies/portfolio-linear.json
hooks-install:
	$(PYTHON) scripts/linear_workspace.py install "$(WORKSPACE)" $(if $(SNAPSHOT),--snapshot "$(SNAPSHOT)",) --policy "$(HOOK_POLICY)"
hooks-refresh:
	$(PYTHON) scripts/linear_workspace.py refresh "$(WORKSPACE)"
hooks-status:
	$(PYTHON) scripts/linear_workspace.py status "$(WORKSPACE)"
hooks-uninstall:
	$(PYTHON) scripts/linear_workspace.py remove "$(WORKSPACE)"

.PHONY: tools check
tools:
	uv sync --frozen --python 3.12
	npm ci --ignore-scripts

check:
	.venv/bin/ruff check checks
	.venv/bin/ruff format --check checks
	.venv/bin/mypy checks
	.venv/bin/python -m unittest discover -s tests -p test_review.py -v
	.venv/bin/python -m unittest discover -s tests -p test_recheck_review.py -v
	$(MAKE) test

.PHONY: governance-test governance-check
governance-test:
	$(PYTHON) -m unittest discover -s tests -p 'test_governance.py' -v

governance-check: governance-test
	$(PYTHON) scripts/audit_governance.py
