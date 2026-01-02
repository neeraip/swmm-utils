# SWMM Utils Examples

This folder contains example scripts demonstrating how to use swmm-utils.

Each example is in its own subfolder and outputs files to that same folder.

## Running Examples

All examples can be run from the project root:

```bash
python examples/example1/example1.py
python examples/example2/example2.py
```

## Available Examples

### example1

**Location:** `examples/example1/example1.py`

Demonstrates:
- Loading a SWMM .inp file (example1.inp)
- Converting to JSON format
- Converting to Parquet format (both single-file and multi-file modes)
- Running the SWMM simulation engine

**Features shown:**
- Using `SwmmInput` context manager
- Accessing model statistics
- Saving to multiple output formats
- Running SWMM simulations via subprocess

**Output files** (in `examples/example1/`):
- `example1.json` - JSON format
- `example1.parquet` - Single-file Parquet
- `example1_parquet/` - Multi-file Parquet (one file per section)
- `example1.rpt` - SWMM simulation report
- `example1.out` - SWMM simulation output

### example2

**Location:** `examples/example2/example2.py`

Demonstrates:
- Loading a SWMM .inp file (example2.inp)
- Converting to JSON format
- Converting to Parquet format (both single-file and multi-file modes)
- Running the SWMM simulation engine

**Features shown:**
- Using `SwmmInput` context manager
- Accessing model statistics
- Saving to multiple output formats
- Running SWMM simulations via subprocess

**Output files** (in `examples/example2/`):
- `example2.json` - JSON format
- `example2.parquet` - Single-file Parquet
- `example2_parquet/` - Multi-file Parquet (one file per section)
- `example2.rpt` - SWMM simulation report
- `example2.out` - SWMM simulation output

## Structure

```
examples/
├── .gitignore       # Ignores output files for all examples
├── README.md
├── example1/
│   ├── example1.py      # Example script
│   ├── example1.inp     # Input file
│   ├── example1.json    # Generated (git-ignored)
│   ├── example1.parquet # Generated (git-ignored)
│   ├── example1_parquet/ # Generated (git-ignored)
│   ├── example1.rpt     # SWMM report (git-ignored)
│   └── example1.out     # SWMM output (git-ignored)
└── example2/
    ├── example2.py      # Example script
    ├── example2.inp     # Input file
    ├── example2.json    # Generated (git-ignored)
    ├── example2.parquet # Generated (git-ignored)
    ├── example2_parquet/ # Generated (git-ignored)
    ├── example2.rpt     # SWMM report (git-ignored)
    └── example2.out     # SWMM output (git-ignored)
```

Each example folder contains:
- The example script (`.py` file)
- The input file (`.inp` file)
- Generated output files (git-ignored by root `examples/.gitignore`)
