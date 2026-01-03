# SWMM Utils Tests

This directory contains comprehensive tests for the SWMM Utils package, covering input (.inp), report (.rpt), and output (.out) file handling.

## Running Tests

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run all tests:
```bash
pytest
```

Run all tests with verbose output:
```bash
pytest -v
```

Run with coverage report:
```bash
pytest --cov=swmm_utils --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_inp.py -v
```

Run specific test class:
```bash
pytest tests/test_out.py::TestSwmmOutput -v
```

Run specific test:
```bash
pytest tests/test_out.py::TestSwmmOutput::test_to_json_with_time_series -v
```

## Test Structure

### Input File Tests (`test_inp.py`)
- SWMM input file (.inp) parsing and high-level interface
- 7 tests covering basic file loading, properties, and round-trip conversions

### Input Decoder/Encoder Tests (`test_inp_decoder_encoder.py`)
- Low-level parsing of SWMM input file sections
- 9 tests covering section parsing, section encoding, and parser robustness

### Input Format Tests (`test_inp_formats.py`)
- Export capabilities for input files (JSON, Parquet)
- 6 tests covering round-trip conversions and format validation

### Output File Tests (`test_out.py`)
- SWMM binary output file (.out) parsing and export
- 29 tests covering:
  - Decoder initialization and file parsing
  - Header and metadata extraction
  - Time index creation
  - High-level interface properties and methods
  - JSON export (metadata-only and with time series)
  - Parquet export (single-file and multi-file modes)
  - File I/O and directory creation

### Report File Tests (`test_rpt.py`)
- SWMM text report file (.rpt) parsing
- 12 tests covering report structure, element data extraction, and interface methods

## Test Coverage Summary

- **Total Tests**: 69
  - Input files: 7 + 9 + 6 = 22 tests
  - Output files: 29 tests
  - Report files: 12 tests
  
- **Coverage Areas**:
  - File parsing and decoding
  - Metadata extraction
  - Time series data handling
  - Export formats (JSON, Parquet)
  - Properties and accessor methods
  - Error handling and edge cases
  - Round-trip conversion (parse → export → parse)

## Writing Tests

When adding new features:
1. Add test cases for new functionality
2. Include edge cases (empty data, missing fields, etc.)
3. Test all export formats (JSON, Parquet if applicable)
4. For output files, test both metadata-only and full time series modes
5. Include round-trip tests where applicable
6. Use descriptive test names and docstrings
7. Group related tests in test classes

## Key Test Patterns

### Testing Metadata-Only Export (Default)
```python
def test_export_metadata_only():
    output = SwmmOutput("file.out")
    output.to_json("output.json")
    # Verify small file size (~4 KB)
```

### Testing Full Time Series Export
```python
def test_export_with_time_series():
    output = SwmmOutput("file.out", load_time_series=True)
    output.to_json("output.json")
    # Verify large file size (500x+ larger)
```

### Testing Round-Trip Conversion
```python
def test_roundtrip_conversion():
    original = SwmmInput("file.inp")
    original.to_json("temp.json")
    # Verify exported data can be re-imported
```

## Test Data

Test data is located in the `examples/` directory:
- `examples/example1/example1.out` - Sample SWMM output file
- `examples/example2/example2.out` - Additional sample SWMM output file
- Various input and report files for comprehensive testing

## Continuous Integration

All tests must pass before merging:
```bash
pytest tests/ -v --tb=short
```

Expected output: **69 tests passing**
