# SWMM Utils Example

This example demonstrates how to use SWMM Utils to decode, modify, and encode SWMM models.

## Running the Example

From the repository root:

```bash
# Make sure swmm-utils is installed in editable mode
pip install -e .

# Run the demo
python example/demo.py
```

## What the Demo Does

1. **Decodes** a SWMM input file (`data/10_Outfalls.inp`) into a Python dictionary
2. **Modifies** the model:
   - Updates the title
   - Adds descriptions to junctions
   - Changes the report step option
3. **Encodes** the modified model into multiple formats:
   - `.inp` - Standard SWMM input file format
   - `.json` - JSON format for easy inspection/integration
   - `.parquet` - Parquet format for efficient data storage (one file per section)
4. **Decodes** from JSON and Parquet formats back into memory
5. **Verifies** round-trip conversion works correctly

## Output

All output files are saved to `example/output/`:

```
example/output/
├── modified_model.inp
├── modified_model.json
├── auto_detected.inp
├── auto_detected.json
├── model_single.parquet          # Single-file Parquet
├── parquet_multifile/             # Multi-file Parquet (one file per section)
│   ├── junctions.parquet
│   ├── outfalls.parquet
│   ├── conduits.parquet
│   └── ... (one file per model section)
└── roundtrip.json
```

## Key Concepts

### Decoding (Parsing)

```python
from swmm_utils import SwmmInputDecoder

decoder = SwmmInputDecoder()

# Decode from .inp file
model = decoder.decode_file("path/to/model.inp")

# Decode from JSON
model = decoder.decode_json("path/to/model.json")
# or from JSON string
model = decoder.decode_json('{"title": "My Model", ...}')

# Decode from Parquet (directory with .parquet files)
model = decoder.decode_parquet("path/to/parquet_dir")

# model is now a Python dict with keys like:
# - "junctions", "outfalls", "conduits", etc.
```

### Modifying

```python
# Models are plain Python dicts - modify them directly
model["title"] = "My Modified Model"
model["junctions"][0]["description"] = "Updated junction"
```

### Encoding

```python
from swmm_utils import SwmmInputEncoder

encoder = SwmmInputEncoder()

# Encode to SWMM .inp format
encoder.encode_to_inp_file(model, "output.inp")

# Encode to JSON
encoder.encode_to_json(model, "output.json", pretty=True)

# Encode to Parquet - Multi-file mode (one file per section, default)
encoder.encode_to_parquet(model, "output_dir", single_file=False)

# Encode to Parquet - Single-file mode (all sections in one file)
encoder.encode_to_parquet(model, "output.parquet", single_file=True)

# Auto-detect format from file extension
encoder.encode_to_file(model, "output.inp")   # .inp format
encoder.encode_to_file(model, "output.json")  # .json format
```

### Decoding from Parquet

```python
from swmm_utils import SwmmInputDecoder

decoder = SwmmInputDecoder()

# Decode from multi-file Parquet (auto-detects directory)
model = decoder.decode_parquet("output_dir")

# Decode from single-file Parquet (auto-detects file)
model = decoder.decode_parquet("output.parquet")
```

## Next Steps

- Try modifying different parts of the model
- Load your own SWMM files
- Use the JSON output to integrate with other tools
- Use Parquet files for efficient data analysis with pandas/polars
