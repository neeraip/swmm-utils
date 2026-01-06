# Copilot Instructions for SWMM Utils

## Project Overview

**SWMM Utils** is a Python utility library for parsing and manipulating EPA SWMM (Storm Water Management Model) files. It supports three file types with consistent architecture:

- **.inp** (input) - SWMM model definitions with typed properties
- **.rpt** (report) - Simulation results extracted from text format
- **.out** (output) - Binary simulation output with optional time series

**Current Status**: 78/78 tests passing, 10.0/10 pylint score, Python 3.8+

---

## Architecture Pattern: Decoder/Encoder

All three file types follow the same architectural pattern:

```
File → Decoder → Dict[str, Any] ← Encoder → File/JSON/Parquet
         ↓
    High-level Interface Class
  (SwmmInput, SwmmReport, SwmmOutput)
         ↓
    Typed Properties & Methods
```

### Key Pattern Rules

1. **Decoder** (e.g., `inp_decoder.py`): Converts files → raw data dicts

   - Returns flat/nested `Dict[str, Any]` with no type hints on dict contents
   - Used by high-level classes via `decoder.decode_file()` or `decode_json()` or `decode_parquet()`
   - Never imports the high-level class; avoids circular dependencies

2. **Encoder** (e.g., `inp_encoder.py`): Converts data dicts → files

   - **Critical**: Accepts `data: Dict[str, Any]` ONLY (not class instances)
   - For `.out` files: Also accepts optional `summary_func: Optional[Callable[[], Dict[str, Any]]]`
   - Handles `.inp`/`.json`/`.parquet` export; `.out` handles `.json`/`.parquet` only
   - Methods: `encode_to_file()` (auto-detects format), `encode_to_json()`, `encode_to_parquet()`, etc.

3. **High-level Class** (e.g., `SwmmInput`, `SwmmOutput`, `SwmmReport`): User-facing interface
   - Instantiates decoder + encoder in `__init__`
   - Stores internal state in `self._data: Dict[str, Any]`
   - Properties expose typed access to `self._data` (e.g., `@property def title(self)`)
   - Export methods delegate to encoder: `self.encoder.encode_to_json(self._data, ...)`
   - Supports context manager: `__enter__` and `__exit__`

### Why This Pattern?

- **Separation of concerns**: Parsing logic isolated from format conversion
- **No circular imports**: Encoders never import high-level classes
- **Reusability**: Decoders/encoders can be used independently for dict-based workflows
- **Extensibility**: Adding new export formats only modifies encoder, not high-level class

---

## Module Organization

```
src/swmm_utils/
├── __init__.py              # Exports all public classes
├── inp.py                   # SwmmInput high-level interface
├── inp_decoder.py           # Parse .inp → dict
├── inp_encoder.py           # Dict → .inp/.json/.parquet
├── out.py                   # SwmmOutput high-level interface
├── out_decoder.py           # Parse .out binary → dict
├── out_encoder.py           # Dict → .json/.parquet
├── rpt.py                   # SwmmReport high-level interface
└── rpt_decoder.py           # Parse .rpt → dict
```

**Test Organization** (matches source structure):

- `test_inp.py` - High-level interface only (7 tests)
- `test_inp_decoder_encoder.py` - Decoder/encoder unit tests (15 tests: 8 decoder + 7 encoder)
- `test_inp_formats.py` - Export format validation (6 tests)
- `test_out.py` - High-level interface (16 tests)
- `test_out_decoder_encoder.py` - Decoder/encoder unit tests (14 tests: 5 decoder + 9 encoder)
- `test_out_formats.py` - Export format validation (8 tests)
- `test_rpt.py` - High-level interface (5 tests)
- `test_rpt_decoder.py` - Decoder unit tests (7 tests)

---

## Critical Developer Workflows

### Running Tests

```bash
# All tests (standard)
pytest

# With verbose output + coverage
pytest -v --cov=src/swmm_utils --cov-report=html

# Specific module
pytest tests/test_inp.py -v

# Specific class/function
pytest tests/test_out_decoder_encoder.py::test_decoder_basic_structure -v
```

### Code Quality Checks

```bash
# Format with black
black src tests setup.py

# Lint with flake8 (integrated in CI)
flake8 src tests

# Run all checks (use Makefile)
make format lint test
```

### Publishing New Features

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Add tests**: Always add to appropriate test file
3. **Run tests**: `pytest -v` must pass (78+ tests)
4. **Lint**: `make format lint` before commit
5. **Commit**: Message format: `feat:` or `fix:` or `refactor:`
6. **Version bump** (if releasing):
   - `make bump-patch` → 0.3.3 → 0.3.4
   - `make bump-minor` → 0.3.3 → 0.4.0

---

## Project-Specific Conventions

### Type Hints

- **Required**: Use `Union[str, Path]` instead of `str | Path` (Python 3.8 compatibility)
- **Dict contents**: Type as `Dict[str, Any]` even if structure is known (matches decoder pattern)
- **Optional**: Use `Optional[X]` instead of `X | None`

### File Format Support

- **SwmmInput**: Load/save `.inp`, `.json`, `.parquet`
- **SwmmOutput**: Load `.out`, export `.json`, `.parquet` (binary .out write not supported)
- **SwmmReport**: Load `.rpt` only (text format, no export)

### Time Series in SwmmOutput

```python
# Load metadata only (default, fast)
output = SwmmOutput("sim.out")

# Load metadata + all time series (memory intensive)
output = SwmmOutput("sim.out", load_time_series=True)
output.to_json("complete.json")  # Includes all timesteps

# Export metadata-only
output.to_json("metadata.json", include_time_series=False)
```

### Error Handling

- **File format errors**: Raise `ValueError` with clear message (e.g., "Unsupported file format: .xyz")
- **Validation errors**: Don't validate in decoders; let raw data pass through
- **File I/O**: Create parent directories: `filepath.parent.mkdir(parents=True, exist_ok=True)`

---

## Common Patterns in Code

### Adding a New Export Format

1. Add method to encoder: `def encode_to_format(self, data: Dict[str, Any], filepath, **kwargs):`
2. Update `encode_to_file()` to recognize format
3. Add high-level method in class: `def to_format(self, filepath, **kwargs):`
4. Add tests in `test_*_formats.py`

**Example** (from `inp_encoder.py`):

```python
def encode_to_json(self, model: Dict[str, Any], filepath: str, pretty: bool = True):
    # Implementation

def encode_to_file(self, model, filepath, file_format=None):
    if file_format == "json":
        self.encode_to_json(model, filepath, pretty=True)
```

### Adding a New Property to High-Level Class

1. Access from `self._data` dict directly
2. Return typed value (perform conversions if needed)
3. Never modify `self._data` in properties (use setter if needed)

**Example** (from `out.py`):

```python
@property
def version(self) -> str:
    return self._data["header"]["version_str"]

@property
def start_date(self) -> datetime:
    return self._data["metadata"]["start_date"]
```

### Adding Decoder Unit Tests

Use module-level functions with `@pytest.mark` for organization. Place in `test_*_decoder_encoder.py`:

```python
# DECODER TESTS
def test_decoder_loads_header(example_inp_file):
    decoder = SwmmInputDecoder()
    data = decoder.decode_file(str(example_inp_file))
    assert "title" in data

# ENCODER TESTS
def test_encoder_writes_json(tmp_path, example_data):
    encoder = SwmmInputEncoder()
    output_file = tmp_path / "output.json"
    encoder.encode_to_json(example_data, str(output_file))
    assert output_file.exists()
```

---

## Integration Points & Dependencies

### External Dependencies

- **pandas** (1.0.0+): Data frame operations for Parquet export
- **pyarrow** (10.0.0+): Parquet read/write
- **pytest** (7.0.0+): Testing framework

### Cross-Module Communication

- High-level classes always instantiate both decoder + encoder
- Encoders export to public API (`__init__.py`)
- No inter-decoder/encoder dependencies (avoid circular imports)

### Data Flow

```
SwmmInput._load("file.inp")
  ↓
SwmmInputDecoder.decode_file("file.inp")
  ↓ (returns)
Dict[str, Any] → SwmmInput._data
  ↓
User accesses properties: inp.title, inp.junctions, etc.
  ↓ (user calls)
SwmmInput.to_json("out.json")
  ↓
SwmmInputEncoder.encode_to_json(self._data, "out.json")
  ↓ (writes to disk)
output.json
```

---

## Validation & Quality Assurance

### Pre-Commit Checklist

- [ ] New tests added (relevant test file)
- [ ] `pytest -v` passes (all 78+ tests)
- [ ] `make format lint` passes
- [ ] Pylint score 10.0/10 maintained
- [ ] No unused imports
- [ ] Type hints for all function signatures (except internal helpers)

### Test Coverage Strategy

- **Unit tests**: Decoder/encoder functions in isolation
- **Integration tests**: High-level interface with real files
- **Format tests**: Round-trip (load → export → load equality)
- **Edge cases**: Empty data, missing fields, large files

---

## Common Pitfalls to Avoid

1. **Circular imports**: Never import high-level class in decoder/encoder
2. **Type mismatch**: Don't use `str | Path`; use `Union[str, Path]`
3. **Dict structure assumptions**: Keep dicts loosely typed (`Dict[str, Any]`)
4. **Missing pytest fixtures**: Use `@pytest.fixture` for shared test data
5. **Incomplete exports**: Always add new classes to `src/swmm_utils/__init__.py` and `__all__`
6. **Parquet column naming**: Use underscores not spaces (required by PyArrow)

---

## Quick Reference: File Locations

| Task                      | File                                | Example                          |
| ------------------------- | ----------------------------------- | -------------------------------- |
| Add input parsing logic   | `src/swmm_utils/inp_decoder.py`     | `def _parse_junctions()`         |
| Add export functionality  | `src/swmm_utils/inp_encoder.py`     | `def _write_junctions()`         |
| Add user-facing method    | `src/swmm_utils/inp.py`             | `def get_junction(name):`        |
| Test high-level interface | `tests/test_inp.py`                 | `def test_load_save_roundtrip()` |
| Test decoder/encoder      | `tests/test_inp_decoder_encoder.py` | `def test_decoder_junctions()`   |
| Test exports              | `tests/test_inp_formats.py`         | `def test_parquet_roundtrip()`   |
| Update version            | `setup.py` + `__init__.py`          | Version string in both files     |

---

## Notes on Recent Refactoring

**Recent change** (January 2026): Refactored `SwmmOutputEncoder` to accept `data: Dict[str, Any]` instead of `SwmmOutput` instance. This:

- Eliminates forward reference string literals (`"SwmmOutput"`)
- Removes tight coupling between encoder and high-level class
- Matches pattern used in `SwmmInputEncoder`
- Requires passing optional `summary_func: Callable[[], Dict[str, Any]]` for summary generation

If you see `.out` export methods, they now follow this pattern:

```python
# ✅ Correct
self.encoder.encode_to_json(self._data, filepath, summary_func=self.summary)

# ❌ Old pattern (avoid)
self.encoder.encode_to_json(self, filepath)
```
