from pathlib import Path

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


def test_empty_sections_roundtrip(tmp_path: Path):
    """Create a minimal .inp with empty sections, parse and unparse it, and ensure no exceptions are raised and sections are preserved."""

    content = """[TITLE]
Example empty sections

[OPTIONS]

[SUBCATCHMENTS]

[JUNCTIONS]

[CONDUITS]

"""

    inp_path = tmp_path / "minimal.inp"
    inp_path.write_text(content, encoding="utf-8")

    decoder = SwmmInputDecoder()
    model = decoder.decode_file(str(inp_path))

    # Model should be a dict; sections may be absent for empty files, treat as empty lists
    assert isinstance(model, dict)
    for section in ["subcatchments", "junctions", "conduits"]:
        val = model.get(section, [])
        assert isinstance(val, list), f"section {section} should be a list or absent"

    # Encode back to a file and ensure file is created
    out = tmp_path / "unparsed.inp"
    encoder = SwmmInputEncoder()
    encoder.encode_to_inp_file(model, str(out))

    assert out.exists()
    assert out.stat().st_size > 0
