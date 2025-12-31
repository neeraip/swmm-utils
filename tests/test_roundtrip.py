import json
from pathlib import Path

import pytest

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


def test_roundtrip_parse_convert_unparse(tmp_path: Path):
    """Parse a sample .inp, convert to JSON, unparse to a new .inp, and verify key counts match."""

    sample_inp = Path("data/10_Outfalls.inp")
    assert (
        sample_inp.exists()
    ), "Sample input file data/10_Outfalls.inp must exist for this test"

    parser = SwmmInputDecoder()
    model = parser.decode_file(str(sample_inp))

    # Basic sanity checks on parsed model
    assert isinstance(model, dict)
    # Record counts for a few representative sections
    counts = {
        "junctions": len(model.get("junctions", [])),
        "outfalls": len(model.get("outfalls", [])),
        "conduits": len(model.get("conduits", [])),
    }

    # Convert to JSON in a temporary dir
    converter = SwmmInputEncoder()
    json_path = tmp_path / "model.json"
    converter.encode_to_json(model, str(json_path), pretty=True)
    assert json_path.exists()

    # Load JSON and ensure it has the same top-level keys
    with open(json_path, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)

    assert isinstance(loaded, dict)
    for k in ["junctions", "outfalls", "conduits"]:
        assert k in loaded
        # JSON arrays should match original counts
        assert len(loaded.get(k, [])) == counts[k]

    # Unparse to a new .inp file and ensure it is created and non-empty
    out_inp = tmp_path / "roundtrip_unparsed.inp"
    unparser = SwmmInputEncoder()
    unparser.encode_to_inp_file(loaded, str(out_inp))

    assert out_inp.exists()
    assert out_inp.stat().st_size > 0

    # Re-parse the unparsed file and compare a few counts to ensure fidelity
    reparsed = parser.decode_file(str(out_inp))
    assert isinstance(reparsed, dict)
    for k in ["junctions", "outfalls", "conduits"]:
        assert len(reparsed.get(k, [])) == counts[k]
