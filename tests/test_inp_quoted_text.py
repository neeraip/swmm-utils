"""
Quoted text in an input file. Before 1.7.1 the decoder kept a label's
quotes in ``text`` and the encoder quoted it again, so every decode →
encode added a pair; a label, profile name or file path with spaces was
split at the first space.
"""
import io

import pytest

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


def _decode(text):
    return SwmmInputDecoder().decode(io.StringIO(text))


def _encode(model):
    buf = io.StringIO()
    SwmmInputEncoder().encode_to_inp(model, buf)
    return buf.getvalue()


def _section(text, name):
    """A section's data lines, comments dropped and blanks collapsed."""
    lines, inside = [], False
    for line in text.splitlines():
        if line.startswith("["):
            inside = line.strip() == f"[{name}]"
        elif inside and line.strip() and not line.startswith(";"):
            lines.append(line)
    return lines


def _assert_stable(text):
    """decode → encode → decode → encode changes nothing after the first pass."""
    first = _encode(_decode(text))
    assert _decode(first) == _decode(text)
    assert _encode(_decode(first)) == first
    return first


LABELS = """[LABELS]
;;X-Coord  Y-Coord  Label
218.836  1149.697  "S1" "" "Arial" 14 0 0
10  20  "Outfall to river"  "J1"  "Arial"  10  1  0
30  40  ""
50  60  "Gage A"
"""


def test_label_text_is_read_without_its_quotes():
    labels = _decode(LABELS)["labels"]
    assert [lab["text"] for lab in labels] == ["S1", "Outfall to river", "", "Gage A"]
    assert labels[0]["anchor"] == '"" "Arial" 14 0 0'
    assert labels[1]["anchor"] == '"J1"  "Arial"  10  1  0'
    assert "anchor" not in labels[2] and "anchor" not in labels[3]


def test_labels_are_written_with_one_pair_of_quotes():
    out = _section(_encode(_decode(LABELS)), "LABELS")
    assert [line.split(None, 2)[2] for line in out] == [
        '"S1" "" "Arial" 14 0 0',
        '"Outfall to river" "J1"  "Arial"  10  1  0',
        '""',
        '"Gage A"',
    ]


def test_labels_round_trip_stably():
    once = _assert_stable(LABELS)
    assert _decode(once)["labels"] == _decode(LABELS)["labels"]


def test_unquoted_label_is_quoted_on_write():
    out = _section(_encode(_decode("[LABELS]\n1 2 Hello\n")), "LABELS")
    assert out[0].split() == ["1", "2", '"Hello"']


def test_label_with_an_embedded_quote_is_stable():
    # SWMM has no escape for a quote inside a label; the row reads as the
    # quoted part followed by the rest, and keeps reading that way.
    _assert_stable('[LABELS]\n1 2 "say "hi"" "" "Arial" 10 0 0\n')


def test_label_text_decoded_by_older_versions_is_not_quoted_again():
    model = {"labels": [{"x": "1", "y": "2", "text": '"S1"', "anchor": '"" "Arial" 14 0 0'}]}
    out = _section(_encode(model), "LABELS")
    assert out[0].split() == ["1", "2", '"S1"', '""', '"Arial"', "14", "0", "0"]


def test_profile_name_with_spaces_is_one_name():
    text = '[PROFILES]\n;;Name  Links\n"Main trunk      " C1 C2 C3\n"P2" C4\n'
    profiles = _decode(text)["profiles"]
    assert profiles[0] == {"name": "Main trunk      ", "links": ["C1", "C2", "C3"]}
    assert profiles[1] == {"name": "P2", "links": ["C4"]}
    out = _section(_assert_stable(text), "PROFILES")
    assert out[0].startswith('"Main trunk      " C1 C2 C3')
    assert out[1].split() == ['"P2"', "C4"]


def test_profile_name_decoded_by_older_versions_is_written_as_before():
    # 1.7.0 split "Main trunk" at the space: the name kept its opening quote.
    model = {"profiles": [{"name": '"Main', "links": ['trunk"', "C1"]}]}
    out = _section(_encode(model), "PROFILES")
    assert out[0].split() == ['"Main', 'trunk"', "C1"]


def test_timeseries_file_path_with_spaces_is_kept_whole():
    text = '[TIMESERIES]\nTS1 FILE "C:\\rain data\\gage 1.dat"\nTS2 0:00 0.5\n'
    ts = _decode(text)["timeseries"]
    assert ts["TS1"] == [{"date": "", "time": "FILE", "value": '"C:\\rain data\\gage 1.dat"'}]
    out = _section(_assert_stable(text), "TIMESERIES")
    assert out[0].split(None, 2) == ["TS1", "FILE", '"C:\\rain data\\gage 1.dat"']


def test_lid_usage_report_file_with_spaces_is_one_column():
    text = ('[LID_USAGE]\nS1 RG 5 2000 4 0 22 1 "D:\\lid reports\\S1 RG.txt" J1 0\n')
    entry = _decode(text)["lid_usage"][0]
    assert entry["rpt_file"] == '"D:\\lid reports\\S1 RG.txt"'
    assert (entry["drain_to"], entry["from_pervious"]) == ("J1", "0")
    out = _section(_assert_stable(text), "LID_USAGE")
    assert out[0].split()[-2:] == ["J1", "0"]
    assert '"D:\\lid reports\\S1 RG.txt"' in out[0]


def test_temperature_file_path_is_kept_as_written():
    text = '[TEMPERATURE]\nFILE "C:\\climate  data\\temps.dat" 01/01/2000\n'
    assert _decode(text)["temperature"]["file"] == '"C:\\climate  data\\temps.dat" 01/01/2000'
    _assert_stable(text)


@pytest.mark.parametrize("text", [
    '[TITLE]\nThe term "outlet control" is a misnomer\n',
    '[OPTIONS]\nTEMPDIR "C:\\temp dir\\"\n',
    '[FILES]\nSAVE HOTSTART "hot start.hsf" 01/01/1998 12:00:00\n',
    '[BACKDROP]\nFILE "C:\\maps\\site plan.png"\n',
    '[RAINGAGES]\nRG1 VOLUME 0:15 1.0 FILE "C:\\rain data\\rg 1.dat" RG1 IN\n',
])
def test_other_quoted_text_is_written_as_read(text):
    name = text[1:text.index("]")]
    out = _assert_stable(text)
    assert [" ".join(line.split()) for line in _section(out, name)] == [
        " ".join(line.split()) for line in _section(text, name)]
