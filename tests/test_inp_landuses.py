"""
[LANDUSES] round trip: the section's columns are the street-sweeping
fields, not a percent-impervious figure it never had.
"""

from swmm_utils import SwmmInput
from swmm_utils.inp_decoder import SwmmInputDecoder
from swmm_utils.inp_encoder import SwmmInputEncoder

INP = """[TITLE]
landuse test

[OPTIONS]
FLOW_UNITS CFS

[LANDUSES]
;;               Sweeping   Fraction   Last
;;Name           Interval   Available  Swept
Agriculture      0          0          0
Commercial       7          0.5        2
Open

[COVERAGES]
S1  Agriculture  100
"""


def test_parses_the_three_sweeping_fields(tmp_path):
    path = tmp_path / "lu.inp"
    path.write_text(INP)
    model = SwmmInput(path).to_dict()
    assert model["landuses"] == [
        {"name": "Agriculture", "sweep_interval": "0", "availability": "0", "last_swept": "0"},
        {"name": "Commercial", "sweep_interval": "7", "availability": "0.5", "last_swept": "2"},
        {"name": "Open"},
    ]


def test_writes_every_column_the_engine_reads(tmp_path):
    path = tmp_path / "lu.inp"
    path.write_text(INP)
    model = SwmmInput(path).to_dict()
    out = tmp_path / "out.inp"
    SwmmInputEncoder().encode_to_file(model, out)
    text = out.read_text()
    section = text.split("[LANDUSES]")[1].split("[")[0]
    rows = [ln.split() for ln in section.splitlines() if ln.strip() and not ln.startswith(";")]
    assert rows == [
        ["Agriculture", "0", "0", "0"],
        ["Commercial", "7", "0.5", "2"],
        ["Open"],
    ]
    # And it reads back as it was written.
    assert SwmmInputDecoder().decode_file(out)["landuses"] == model["landuses"]


def test_a_data_json_from_the_old_reading_still_renders(tmp_path):
    """``percent_imperv`` was the sweep interval under the old name."""
    model = {"landuses": [{"name": "Residential", "percent_imperv": "14"}]}
    out = tmp_path / "out.inp"
    SwmmInputEncoder().encode_to_file(model, out)
    section = out.read_text().split("[LANDUSES]")[1].split("[")[0]
    rows = [ln.split() for ln in section.splitlines() if ln.strip() and not ln.startswith(";")]
    assert rows == [["Residential", "14"]]
