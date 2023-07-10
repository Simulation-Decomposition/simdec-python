.PHONY: help prepare doc test serve
.DEFAULT_GOAL := help
SHELL:=/bin/bash

# Add help text after each target name starting with '\#\#'
help:   ## show this help
	@echo -e "Help for this makefile\n"
	@echo "Possible commands are:"
	@grep -h "##" $(MAKEFILE_LIST) | grep -v grep | sed -e 's/\(.*\):.*##\(.*\)/    \1: \2/'

prepare:  ## Install dependencies and pre-commit hook
	pip install -e ".[dev]"
	pre-commit install

doc:  ## Build Sphinx documentation
	sphinx-build -b html docs docs/html

test:  ## Run tests with coverage
	pytest --cov simdec --cov-report term-missing

serve-dev:  ## Serve Panel dashboard - Dev mode
	panel serve app.py --show --autoreload

serve:  ## Serve Panel dashboard - Prod mode
	panel serve app.py
