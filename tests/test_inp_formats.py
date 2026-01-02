"""Test SWMM .inp file format conversions (JSON and Parquet).

Tests encoding and decoding between .inp, JSON, and Parquet formats.
"""

from pathlib import Path
import pytest

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


def test_json_roundtrip(tmp_path: Path):
    """Test encoding to JSON and decoding back."""
    sample_inp = Path("examples/example1/example1.inp")

    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Decode original .inp file
    original_model = decoder.decode_file(str(sample_inp))

    # Encode to JSON
    json_path = tmp_path / "model.json"
    encoder.encode_to_json(original_model, str(json_path), pretty=True)

    # Decode from JSON
    json_model = decoder.decode_json(str(json_path))

    # Verify key sections match
    assert "junctions" in json_model
    assert "outfalls" in json_model
    assert "conduits" in json_model

    assert len(json_model["junctions"]) == len(original_model["junctions"])
    assert len(json_model["outfalls"]) == len(original_model["outfalls"])
    assert len(json_model["conduits"]) == len(original_model["conduits"])


def test_json_string_decode():
    """Test decoding from JSON string."""
    decoder = SwmmInputDecoder()

    json_str = '{"title": "Test Model", "junctions": [{"name": "J1"}]}'
    model = decoder.decode_json(json_str)

    assert model["title"] == "Test Model"
    assert len(model["junctions"]) == 1
    assert model["junctions"][0]["name"] == "J1"


def test_parquet_roundtrip(tmp_path: Path):
    """Test encoding to Parquet (multi-file) and decoding back."""
    sample_inp = Path("examples/example1/example1.inp")

    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Decode original .inp file
    original_model = decoder.decode_file(str(sample_inp))

    # Encode to Parquet (multi-file mode)
    parquet_dir = tmp_path / "parquet"
    encoder.encode_to_parquet(original_model, str(parquet_dir), single_file=False)

    # Verify parquet files were created
    parquet_files = list(parquet_dir.glob("*.parquet"))
    assert len(parquet_files) > 0

    # Decode from Parquet
    parquet_model = decoder.decode_parquet(str(parquet_dir))

    # Verify key sections match
    assert "junctions" in parquet_model
    assert "outfalls" in parquet_model
    assert "conduits" in parquet_model

    assert len(parquet_model["junctions"]) == len(original_model["junctions"])
    assert len(parquet_model["outfalls"]) == len(original_model["outfalls"])
    assert len(parquet_model["conduits"]) == len(original_model["conduits"])


def test_parquet_single_file_roundtrip(tmp_path: Path):
    """Test encoding to Parquet (single-file) and decoding back."""
    sample_inp = Path("examples/example1/example1.inp")

    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Decode original .inp file
    original_model = decoder.decode_file(str(sample_inp))

    # Encode to Parquet (single-file mode)
    parquet_file = tmp_path / "model.parquet"
    encoder.encode_to_parquet(original_model, str(parquet_file), single_file=True)

    # Verify file was created
    assert parquet_file.exists()
    assert parquet_file.is_file()

    # Decode from Parquet
    parquet_model = decoder.decode_parquet(str(parquet_file))

    # Verify key sections match
    assert "junctions" in parquet_model
    assert "outfalls" in parquet_model
    assert "conduits" in parquet_model

    assert len(parquet_model["junctions"]) == len(original_model["junctions"])
    assert len(parquet_model["outfalls"]) == len(original_model["outfalls"])
    assert len(parquet_model["conduits"]) == len(original_model["conduits"])


def test_parquet_missing_directory():
    """Test that decoding from non-existent directory raises error."""
    decoder = SwmmInputDecoder()

    with pytest.raises(FileNotFoundError):
        decoder.decode_parquet("/nonexistent/directory")


def test_full_roundtrip_all_formats(tmp_path: Path):
    """Test complete roundtrip: .inp → JSON → dict → Parquet → dict → .inp"""
    sample_inp = Path("examples/example1/example1.inp")

    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Step 1: Decode from .inp
    model1 = decoder.decode_file(str(sample_inp))

    # Step 2: Encode to JSON and decode back
    json_path = tmp_path / "model.json"
    encoder.encode_to_json(model1, str(json_path))
    model2 = decoder.decode_json(str(json_path))

    # Step 3: Encode to Parquet and decode back
    parquet_dir = tmp_path / "parquet"
    encoder.encode_to_parquet(model2, str(parquet_dir))
    model3 = decoder.decode_parquet(str(parquet_dir))

    # Step 4: Encode back to .inp
    final_inp = tmp_path / "final.inp"
    encoder.encode_to_inp_file(model3, str(final_inp))

    # Verify final file exists and has content
    assert final_inp.exists()
    assert final_inp.stat().st_size > 0

    # Decode the final .inp to verify it's still valid
    final_model = decoder.decode_file(str(final_inp))

    # Core sections should still be present
    assert "junctions" in final_model
    assert "outfalls" in final_model
    assert "conduits" in final_model
