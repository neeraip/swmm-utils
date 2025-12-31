# SWMM Parser Tests

This directory contains tests for the SWMM parser package.

## Running Tests

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=swmm_parser --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_parser.py -v
```

## Test Structure

- `test_parser.py` - Core parser/unparser functionality tests
- Sample SWMM input data embedded in test fixtures
- Round-trip conversion tests
- JSON/Parquet conversion tests

## Writing Tests

When adding new features:
1. Add test cases for new section parsers
2. Include edge cases (empty sections, comments, etc.)
3. Test round-trip conversion
4. Update test data samples as needed
