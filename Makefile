PYTHON ?= .venv/bin/python

.PHONY: install test lint format serve eval

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests

serve:
	$(PYTHON) -m ordbro serve

eval:
	$(PYTHON) -m ordbro eval all
