"""
Report excerpts from EPA SWMM 5.2.4 and OpenSWMM 6.0.0-alpha.3 runs of the
same synthetic model (two junctions, an outfall, one subcatchment).
"""
from swmm_utils import SwmmReportDecoder

SWMM5_HEADER = """
  EPA STORM WATER MANAGEMENT MODEL - VERSION 5.2 (Build 5.2.4)
  ------------------------------------------------------------

  Synthetic repro

  ****************
  Analysis Options
  ****************
"""

OPENSWMM_HEADER = """  OPENSWMM ENGINE - VERSION 6.0.0-alpha.3
  -------------------------------------------
  ;;Project Title/Notes
  Synthetic repro

  ****************
  Analysis Options
  ****************
"""

OPENSWMM_LEGACY_HEADER = """
  OPENSWMM ENGINE - VERSION 5.3.0 (Build 5.3.0)
  ------------------------------------------------------------

  Synthetic repro
"""

UNTITLED_HEADER = """
  EPA STORM WATER MANAGEMENT MODEL - VERSION 5.2 (Build 5.2.4)
  ------------------------------------------------------------

  WARNING 04: minimum elevation drop used for Conduit C1

  *************
  Element Count
  *************
"""

NO_SURCHARGE_NO_FLOODING = """
  **********************
  Node Surcharge Summary
  **********************

  No nodes were surcharged.


  *********************
  Node Flooding Summary
  *********************

  No nodes were flooded.


  **********************
  Storage Volume Summary
  **********************

  ------------------------------------------------------------------------------------------------
                         Average    Avg   Evap  Exfil     Maximum    Max    Time of Max    Maximum
                          Volume   Pcnt   Pcnt   Pcnt      Volume   Pcnt     Occurrence    Outflow
  Storage Unit          1000 ft3   Full   Loss   Loss    1000 ft3   Full    days hr:min        CFS
  ------------------------------------------------------------------------------------------------
  SU1                      1.250   12.0    0.0    0.0       4.000   40.0       0  03:10      0.500


  ***********************
  Outfall Loading Summary
  ***********************
"""

NO_SURCHARGE = """
  **********************
  Node Surcharge Summary
  **********************

  No nodes were surcharged.


  *********************
  Node Flooding Summary
  *********************

  Flooding refers to all water that overflows a node, whether it ponds or not.
  --------------------------------------------------------------------------
                                                             Total   Maximum
                                 Maximum   Time of Max       Flood    Ponded
                        Hours       Rate    Occurrence      Volume     Depth
  Node                 Flooded       CFS   days hr:min    10^6 gal      Feet
  --------------------------------------------------------------------------
  J1                      2.05      4.84      0  01:05       0.161     0.000


  ***********************
  Outfall Loading Summary
  ***********************
"""

SURCHARGE = """
  **********************
  Node Surcharge Summary
  **********************

  Surcharging occurs when water rises above the top of the highest conduit.
  ---------------------------------------------------------------------
                                               Max. Height   Min. Depth
                                   Hours       Above Crown    Below Rim
  Node                 Type      Surcharged           Feet         Feet
  ---------------------------------------------------------------------
  J1                   JUNCTION        2.22          3.000        0.000
  Node                 JUNCTION        2.17          1.832        1.168


  *********************
  Node Flooding Summary
  *********************
"""


def _decode(tmp_path, text):
    path = tmp_path / "model.rpt"
    path.write_text(text)
    return SwmmReportDecoder().decode_file(path)


def test_swmm5_header(tmp_path):
    header = _decode(tmp_path, SWMM5_HEADER)["header"]
    assert header == {"engine": "EPA SWMM", "version": "5.2", "build": "5.2.4",
                      "title": "Synthetic repro"}


def test_openswmm_header(tmp_path):
    header = _decode(tmp_path, OPENSWMM_HEADER)["header"]
    # No build on 6.0; the [TITLE] comment line is not the title.
    assert header == {"engine": "OpenSWMM", "version": "6.0.0-alpha.3",
                      "title": "Synthetic repro"}


def test_openswmm_legacy_engine_header(tmp_path):
    header = _decode(tmp_path, OPENSWMM_LEGACY_HEADER)["header"]
    assert header == {"engine": "OpenSWMM", "version": "5.3.0", "build": "5.3.0",
                      "title": "Synthetic repro"}


def test_a_warning_after_the_banner_is_not_a_title(tmp_path):
    header = _decode(tmp_path, UNTITLED_HEADER)["header"]
    assert "title" not in header and header["version"] == "5.2"


def test_no_nodes_surcharged_reads_no_rows(tmp_path):
    data = _decode(tmp_path, NO_SURCHARGE)
    assert data["node_surcharge"] == []
    assert data["node_flooding"][0]["name"] == "J1"


def test_no_nodes_surcharged_or_flooded_reads_no_rows(tmp_path):
    # The storage table that follows used to be read as surcharge rows.
    data = _decode(tmp_path, NO_SURCHARGE_NO_FLOODING)
    assert data["node_surcharge"] == []
    assert data["node_flooding"] == "No nodes were flooded"
    assert [s["storage_unit"] for s in data["storage_volume"]] == ["SU1"]


def test_surcharge_rows_are_read(tmp_path):
    rows = _decode(tmp_path, SURCHARGE)["node_surcharge"]
    assert [r["node_name"] for r in rows] == ["J1", "Node"]
    assert rows[0] == {"node_name": "J1", "node_type": "JUNCTION", "hours_surcharged": 2.22,
                       "max_height_above_crown": 3.0, "min_depth_below_rim": 0.0}
