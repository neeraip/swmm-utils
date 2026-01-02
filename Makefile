.PHONY: help install install-dev test test-cov lint format clean bump-patch bump-minor bump-major example1 example2

help:
	@echo "SWMM Utils Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install         Install the package in development mode"
	@echo "  install-dev     Install the package with dev dependencies"
	@echo "  test            Run tests"
	@echo "  test-cov        Run tests with coverage report"
	@echo "  lint            Run linting (flake8)"
	@echo "  format          Format code with black"
	@echo "  clean           Remove build artifacts and cache files"
	@echo "  bump-patch      Bump patch version (e.g., 0.2.1 -> 0.2.2)"
	@echo "  bump-minor      Bump minor version (e.g., 0.2.1 -> 0.3.0)"
	@echo "  bump-major      Bump major version (e.g., 0.2.1 -> 1.0.0)"
	@echo "  example1        Run example 1"
	@echo "  example2        Run example 2"
	@echo ""

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=src/swmm_utils --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	flake8 src tests

format:
	black src tests setup.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov .mypy_cache
	@echo "Cleaned up build artifacts and cache"

bump-patch:
	bump2version patch
	git push origin main
	git push origin --tags

bump-minor:
	bump2version minor
	git push origin main
	git push origin --tags

bump-major:
	bump2version major
	git push origin main
	git push origin --tags

example1:
	python examples/example1/example1.py

example2:
	python examples/example2/example2.py
