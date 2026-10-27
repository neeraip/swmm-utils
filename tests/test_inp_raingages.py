"""
[RAINGAGES] source columns: ``FILE Fname Station Units [Start] [SCF]`` and
``TIMESERIES Series [SCF]``, the grammar OpenSWMM reads (its GageData.hpp).
EPA SWMM 5.2.4 reads the start date and ignores the scale factor.
"""
import io

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

INP = """[RAINGAGES]
;;Name  Format  Interval SCF Source
RG1  VOLUME     0:01  1.00  FILE "rain.dat" RG1 MM * 30
RG2  INTENSITY  1:00  1.0   FILE "rain.dat" STA2 IN 01/01/2024
RG3  INTENSITY  1:00  1.0   FILE "rain.dat" STA3 IN
RG4  INTENSITY  0:05  1.0   TIMESERIES RAIN 0.5
RG5  INTENSITY  0:05  1.0   TIMESERIES RAIN
RG6  VOLUME     0:15  1.0   FILE "C:\\rain data\\gage 6.dat" RG6 MM
"""


def _gages(text=INP):
    model = SwmmInputDecoder().decode(io.StringIO(text))
    return model, {g["name"]: g for g in model["raingages"]}


def _encode(model):
    buf = io.StringIO()
    SwmmInputEncoder().encode_to_inp(model, buf)
    return buf.getvalue()


def test_file_start_and_scale_factor_are_read():
    _, g = _gages()
    assert g["RG1"]["data_param"] == "rain.dat"
    assert (g["RG1"]["station"], g["RG1"]["units"]) == ("RG1", "MM")
    assert (g["RG1"]["start"], g["RG1"]["scale_factor"]) == ("*", "30")
    assert g["RG2"]["start"] == "01/01/2024" and "scale_factor" not in g["RG2"]
    assert "start" not in g["RG3"] and "scale_factor" not in g["RG3"]


def test_timeseries_scale_factor_is_read():
    _, g = _gages()
    assert (g["RG4"]["data_param"], g["RG4"]["scale_factor"]) == ("RAIN", "0.5")
    assert "scale_factor" not in g["RG5"]


def test_quoted_file_name_with_spaces_stays_one_column():
    _, g = _gages()
    assert g["RG6"]["data_param"] == "C:\\rain data\\gage 6.dat"
    assert (g["RG6"]["station"], g["RG6"]["units"]) == ("RG6", "MM")


def test_source_columns_are_written_back_as_read():
    model, _ = _gages()
    text = _encode(model)
    assert text.rstrip().endswith('FILE      "C:\\rain data\\gage 6.dat" RG6 MM')
    for tail in ('FILE      "rain.dat" RG1 MM * 30', 'FILE      "rain.dat" STA2 IN 01/01/2024',
                 "TIMESERIES RAIN 0.5"):
        assert tail in text
    assert _gages(text)[1] == _gages()[1]


def test_gage_built_from_fields_writes_its_source_columns():
    model = {"raingages": [
        {"name": "RG1", "format": "VOLUME", "interval": "0:01", "scf": "1.0", "source": "FILE",
         "data_param": "rain.dat", "station": "RG1", "units": "MM", "scale_factor": "30"},
        {"name": "RG2", "format": "INTENSITY", "interval": "0:05", "scf": "1.0", "source": "TIMESERIES",
         "data_param": "RAIN", "scale_factor": "0.5"},
    ]}
    _, g = _gages(_encode(model))
    assert g["RG1"]["file_or_station"] == '"rain.dat" RG1 MM * 30'
    assert g["RG2"]["file_or_station"] == "RAIN 0.5"
