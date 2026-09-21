"""
The numpy-backed time-series reader, against a synthetic .out.

The example .out files are not committed — they need a SWMM binary to
produce — so the decoder tests that read them are skipped in CI. This file
writes a small, valid .out from the format the decoder documents and checks
the reader against known values, so the path that failed on the 4,400-node
Raytown run is exercised on every push.
"""

import struct
from datetime import datetime, timedelta

import numpy as np
import pytest

from swmm_utils import SwmmOutput
from swmm_utils.out_decoder import SwmmOutputDecoder, TimeSeriesRecords

MAGIC = 516114522
N_SYSTEM_VARS = 15


def _s(f, text: str) -> None:
    raw = text.encode("utf-8")
    f.write(struct.pack("<i", len(raw)))
    f.write(raw)


def write_out(
    path,
    *,
    nodes=("J1", "J2"),
    links=("C1",),
    subcatchments=("S1",),
    n_periods=4,
    n_node_vars=6,
    n_link_vars=5,
    n_sub_vars=8,
    value=None,
    truncate_periods=0,
):
    """
    A .out with ``value(role, period, element, var)`` at every slot.

    ``truncate_periods`` drops that many records from the end while the
    footer still claims ``n_periods`` — a run that stopped early.
    """
    value = value or (lambda role, p, e, v: float(p * 100 + e * 10 + v))
    with open(path, "wb") as f:
        f.write(struct.pack("<7i", MAGIC, 52001, 0, len(subcatchments), len(nodes), len(links), 0))
        for label in subcatchments:
            _s(f, label)
        for label in nodes:
            _s(f, label)
        for label in links:
            _s(f, label)
        # Properties: subcatchments (area), nodes (type, invert, max_depth), links (type, offsets, length).
        f.write(struct.pack("<2i", 1, 1))
        for _ in subcatchments:
            f.write(struct.pack("<f", 1.0))
        f.write(struct.pack("<4i", 3, 0, 2, 3))
        for _ in nodes:
            f.write(struct.pack("<i2f", 0, 100.0, 5.0))
        f.write(struct.pack("<5i", 4, 0, 4, 4, 5))
        for _ in links:
            f.write(struct.pack("<i3f", 0, 0.0, 0.0, 300.0))
        # Variable codes per role.
        f.write(struct.pack("<i", n_sub_vars) + struct.pack(f"<{n_sub_vars}i", *range(n_sub_vars)))
        f.write(struct.pack("<i", n_node_vars) + struct.pack(f"<{n_node_vars}i", *range(n_node_vars)))
        f.write(struct.pack("<i", n_link_vars) + struct.pack(f"<{n_link_vars}i", *range(n_link_vars)))
        f.write(struct.pack("<i", N_SYSTEM_VARS) + struct.pack(f"<{N_SYSTEM_VARS}i", *range(N_SYSTEM_VARS)))
        # Start date (Excel serial for 2024-02-13) and a 1-minute report step.
        f.write(struct.pack("<d", 45335.0))
        f.write(struct.pack("<i", 60))
        results_pos = f.tell()
        for p in range(n_periods - truncate_periods):
            f.write(struct.pack("<d", 45335.0 + p / 1440))
            for e, _ in enumerate(subcatchments):
                f.write(struct.pack(f"<{n_sub_vars}f", *[value("subcatchments", p, e, v) for v in range(n_sub_vars)]))
            for e, _ in enumerate(nodes):
                f.write(struct.pack(f"<{n_node_vars}f", *[value("nodes", p, e, v) for v in range(n_node_vars)]))
            for e, _ in enumerate(links):
                f.write(struct.pack(f"<{n_link_vars}f", *[value("links", p, e, v) for v in range(n_link_vars)]))
            f.write(struct.pack(f"<{N_SYSTEM_VARS}f", *[value("system", p, 0, v) for v in range(N_SYSTEM_VARS)]))
        # Footer: ids pos, properties pos, results pos, n_periods, error code, magic.
        f.write(struct.pack("<6i", 0, 0, results_pos, n_periods, 0, MAGIC))
    return path


@pytest.fixture
def out_path(tmp_path):
    return write_out(tmp_path / "synthetic.out")


def test_arrays_have_the_documented_shapes_and_values(out_path):
    data = SwmmOutputDecoder().decode_file(out_path, include_time_series=True)
    arrays = data["time_series_arrays"]

    assert arrays["nodes"].shape == (4, 2, 6)
    assert arrays["links"].shape == (4, 1, 5)
    assert arrays["subcatchments"].shape == (4, 1, 8)
    assert arrays["system"].shape == (4, N_SYSTEM_VARS)
    assert arrays["nodes"].dtype == np.float32

    # value(role, period, element, var) = period*100 + element*10 + var
    assert arrays["nodes"][2, 1, 3] == pytest.approx(213.0)
    assert arrays["links"][3, 0, 4] == pytest.approx(304.0)
    assert arrays["subcatchments"][1, 0, 7] == pytest.approx(107.0)
    assert arrays["system"][0, 14] == pytest.approx(14.0)


def test_arrays_are_views_of_one_buffer(out_path):
    """The point of the change: the file's floats once, not a copy per role."""
    data = SwmmOutputDecoder().decode_file(out_path, include_time_series=True)
    arrays = data["time_series_arrays"]
    base = arrays["nodes"].base
    assert base is not None
    assert all(arrays[role].base is base for role in ("subcatchments", "links", "system"))


def test_time_series_records_keep_the_old_shape(out_path):
    data = SwmmOutputDecoder().decode_file(out_path, include_time_series=True)
    ts = data["time_series"]

    assert isinstance(ts, TimeSeriesRecords)
    assert set(ts) == {"subcatchments", "nodes", "links", "system"}
    assert "J2" in ts["nodes"]
    assert "nope" not in ts["nodes"]

    records = ts["nodes"]["J2"]
    assert len(records) == 4
    assert records[2]["timestamp"] == (datetime(2024, 2, 13) + timedelta(minutes=2)).isoformat()
    assert records[2]["values"] == pytest.approx([210.0, 211.0, 212.0, 213.0, 214.0, 215.0])
    assert isinstance(records[2]["values"][0], float)

    assert len(ts["system"]) == 4
    assert ts["system"][1]["values"][0] == pytest.approx(100.0)

    full = ts.to_dict()
    assert full["links"]["C1"][0]["values"] == pytest.approx([0.0, 1.0, 2.0, 3.0, 4.0])


def test_to_json_writes_the_records(out_path, tmp_path):
    import json

    SwmmOutput(out_path, load_time_series=True).to_json(tmp_path / "o.json")
    data = json.loads((tmp_path / "o.json").read_text())
    assert data["time_series"]["nodes"]["J1"][1]["values"][2] == pytest.approx(102.0)


def test_dataframes_match_the_record_walking_builder(out_path):
    """The array fast path must produce what the old builder produced."""
    pd = pytest.importorskip("pandas")
    from swmm_utils.out_encoder import SwmmOutputEncoder

    output = SwmmOutput(out_path, load_time_series=True)
    fast = output.to_dataframe("nodes")

    legacy_data = dict(output._data)
    legacy_data["time_series_arrays"] = None
    legacy = SwmmOutputEncoder().encode_to_dataframe(legacy_data, element_type="nodes")

    pd.testing.assert_frame_equal(fast, legacy, check_index_type=False)
    assert fast.index.names == ["timestamp", "element_name"]
    # Element-major, as before: every period of J1, then J2.
    assert list(fast.index.get_level_values("element_name")[:5]) == ["J1"] * 4 + ["J2"]

    one = output.to_dataframe("links", "C1")
    legacy_one = SwmmOutputEncoder().encode_to_dataframe(legacy_data, element_type="links", element_name="C1")
    pd.testing.assert_frame_equal(one, legacy_one, check_index_type=False, check_names=False)
    assert isinstance(one["value_0"].max(), float)

    assert output.to_dataframe("links", "missing").empty


def test_a_truncated_file_reads_nan_for_the_missing_periods(tmp_path):
    path = write_out(tmp_path / "short.out", n_periods=5, truncate_periods=2)
    arrays = SwmmOutputDecoder().decode_file(path, include_time_series=True)["time_series_arrays"]

    assert arrays["nodes"].shape == (5, 2, 6)
    assert np.isfinite(arrays["nodes"][:3]).all()
    assert np.isnan(arrays["nodes"][3:]).all()


def test_summary_reduces_off_the_arrays(out_path):
    from swmm_utils.exports import _per_feature_summary

    summary = _per_feature_summary(out_path)
    j2 = summary["nodes"]["J2"]
    # period*100 + 10 + var over periods 0..3 → var 0: 10, 110, 210, 310
    assert j2["depth"] == {"min": 10.0, "max": 310.0, "mean": 160.0}
    assert set(j2) == {"depth", "head", "volume", "lateral_inflow", "total_inflow", "flooding"}
    assert summary["links"]["C1"]["capacity"]["max"] == pytest.approx(304.0)
    # SWMM's eight subcatchment variables: five canonical, three positional.
    assert "value_7" in summary["subcatchments"]["S1"]


def test_summary_skips_a_metric_the_run_never_reached(tmp_path):
    from swmm_utils.exports import _per_feature_summary

    path = write_out(tmp_path / "short.out", n_periods=5, truncate_periods=1)
    summary = _per_feature_summary(path)
    assert summary["nodes"]["J1"] == {}


def test_summary_matches_the_dataframe_path(out_path):
    """Same numbers as the groupby that used to produce them."""
    pytest.importorskip("pandas")
    from swmm_utils.exports import _NODE_METRICS, _per_feature_summary, _summarize_per_feature

    output = SwmmOutput(out_path, load_time_series=True)
    legacy = _summarize_per_feature(output.to_dataframe("nodes"), _NODE_METRICS)
    assert _per_feature_summary(out_path)["nodes"] == legacy


def test_cube_is_the_array_transposed(out_path):
    from swmm_utils.exports import _array_to_cube

    arrays = SwmmOutputDecoder().decode_file(out_path, include_time_series=True)["time_series_arrays"]
    cube = _array_to_cube(arrays["nodes"], 2, 4, 6)
    assert cube.shape == (2, 4, 6)
    assert cube.dtype == np.float32
    assert cube[1, 2, 3] == pytest.approx(213.0)
    # Fewer variables than metrics leaves the rest NaN; no array at all is all NaN.
    assert np.isnan(_array_to_cube(arrays["links"], 1, 4, 6)[0, 0, 5])
    assert np.isnan(_array_to_cube(None, 1, 4, 6)).all()


def test_parquet_rows_come_straight_from_the_arrays(out_path, tmp_path):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    from swmm_utils.exports import _role_table

    arrays = SwmmOutputDecoder().decode_file(out_path, include_time_series=True)["time_series_arrays"]
    table = _role_table(
        arrays["nodes"], ["J1", "J2"], role="node",
        metrics=("depth", "head", "volume", "lateral_inflow", "total_inflow", "flooding"),
        element_type_by_id={"J1": "junction"}, step_seconds=60,
    )
    assert table.num_rows == 8
    assert table.schema.field("fid").type == pa.string()
    rows = table.to_pylist()
    assert rows[0]["fid"] == "J1" and rows[0]["element_type"] == "junction"
    assert rows[4]["fid"] == "J2" and rows[4]["element_type"] == "node"
    assert rows[5]["period_idx"] == 1 and rows[5]["period_seconds"] == 60
    assert rows[5]["depth"] == pytest.approx(110.0)
    assert rows[5]["flow_rate"] is None

    pq.write_table(table, tmp_path / "t.parquet")
    assert pq.read_table(tmp_path / "t.parquet").num_rows == 8
