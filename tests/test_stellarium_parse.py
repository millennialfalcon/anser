"""Tests for parsing Stellarium's index.json into figure edges."""

import json
from pathlib import Path

import pytest

from anser.stellarium_parse import normalize_id


@pytest.mark.parametrize(
    "raw, expected",
    [
        (95771, "hip:95771"),  # Alpha Vulpeculae, a JSON int
        ("5350358584482202880", "gaia_dr3:5350358584482202880"),  # a Gaia ID, a JSON string
        ("DSO:IC2602", "dso:IC2602"),  # the Shadow Cross's line to the Southern Pleiades
    ],
)
def test_normalize_id(raw, expected):
    assert normalize_id(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        True,  # bool is a subclass of int in Python, so it sneaks past isinstance(x, int)
        95771.0,  # a float isn't a HIP number
        -5,  # HIP numbers are positive
        0,  # not a HIP number, and an int should never turn into a Gaia ID
        "٣٤",  # Arabic-Indic digits pass str.isdecimal() but aren't a Gaia ID
        "",
        "abc",
        "DSO:",  # prefix with no object
        None,
    ],
)
def test_normalize_id_rejects_junk(raw):
    with pytest.raises(ValueError):
        normalize_id(raw)


# --- figure_edges: a figure's polylines become sorted, deduplicated edge pairs ---

from anser.stellarium_parse import figure_edges  # noqa: E402

COATHANGER = [[95818, 95700, 95584, 95487, 95340, 95291], [95584, 95560, 95582, 95498, 95432]]


def test_vulpecula_is_one_edge():
    assert figure_edges([[95771, 98543]]) == [("hip:95771", "hip:98543")]


def test_pairs_are_sorted_whichever_way_the_line_runs():
    assert figure_edges([[98543, 95771]]) == [("hip:95771", "hip:98543")]


def test_closed_loop_counts_each_edge_once():
    # Summer Triangle: Vega, Altair, Deneb, back to Vega.
    edges = figure_edges([[91262, 97649, 102098, 91262]])
    assert len(edges) == 3


def test_coathanger_is_nine_edges_over_ten_stars():
    edges = figure_edges(COATHANGER)
    stars = {s for pair in edges for s in pair}
    assert len(edges) == 9
    assert len(stars) == 10


def test_same_edge_in_two_lines_appears_once():
    assert figure_edges([[1, 2], [2, 1]]) == [("hip:1", "hip:2")]


def test_mixed_catalogs_in_one_edge():
    assert figure_edges([[57632, "5350358584482202880"]]) == [
        ("gaia_dr3:5350358584482202880", "hip:57632")
    ]


def test_output_is_sorted():
    edges = figure_edges(COATHANGER)
    assert edges == sorted(edges)


@pytest.mark.parametrize(
    "lines",
    [
        [[5, 5]],  # an edge from a star to itself
        [[5]],  # a line with one point draws nothing
        [[]],
    ],
)
def test_degenerate_lines_raise(lines):
    with pytest.raises(ValueError):
        figure_edges(lines)


# --- parse_sky_culture: a loaded index.json becomes one row per edge ---

from anser.stellarium_parse import parse_sky_culture  # noqa: E402

COLUMNS = {"sky_culture", "figure_id", "kind", "star_a", "star_b"}

FIXTURE = {
    "id": "modern",
    "edges": ["001:002 M+ 22:52:00 +34:30:00 22:52:00 +52:30:00 AND LAC"],  # IAU boundaries, not figure lines
    "constellations": [
        {"id": "CON modern Vul", "lines": [[95771, 98543]]},
    ],
    "asterisms": [
        {"id": "AST modern CoH", "common_name": {"english": "Coathanger"}, "lines": COATHANGER},
        {"id": "AST modern STr", "lines": [[91262, 97649, 102098, 91262]]},
        {"id": "AST modern ShC", "lines": [[54294, "DSO:IC2602"], [54301, "5350358584482202880"]]},
        {"id": "AST modern RH1", "is_ray_helper": True, "lines": [[67301, 69673, 65474]]},
    ],
}


def rows_for(rows, figure_id):
    return [r for r in rows if r["figure_id"] == figure_id]


def test_rows_have_exactly_the_five_columns():
    rows = parse_sky_culture(FIXTURE)
    assert rows
    assert all(set(r) == COLUMNS for r in rows)


def test_vulpecula_row():
    assert rows_for(parse_sky_culture(FIXTURE), "CON modern Vul") == [
        {
            "sky_culture": "modern",
            "figure_id": "CON modern Vul",
            "kind": "constellation",
            "star_a": "hip:95771",
            "star_b": "hip:98543",
        }
    ]


def test_kind_comes_from_which_list_the_figure_is_in():
    rows = parse_sky_culture(FIXTURE)
    assert {r["kind"] for r in rows_for(rows, "AST modern CoH")} == {"asterism"}


def test_edge_counts_per_figure():
    rows = parse_sky_culture(FIXTURE)
    assert len(rows_for(rows, "AST modern CoH")) == 9
    assert len(rows_for(rows, "AST modern STr")) == 3


def test_ray_helpers_are_skipped():
    assert rows_for(parse_sky_culture(FIXTURE), "AST modern RH1") == []


def test_dso_point_is_kept():
    stars = {s for r in rows_for(parse_sky_culture(FIXTURE), "AST modern ShC") for s in (r["star_a"], r["star_b"])}
    assert "dso:IC2602" in stars


def test_bad_star_error_names_the_figure():
    broken = {"id": "modern", "constellations": [{"id": "CON modern Bad", "lines": [[1, "oops"]]}], "asterisms": []}
    with pytest.raises(ValueError, match="CON modern Bad"):
        parse_sky_culture(broken)


# --- the real file, if it's been fetched ---

REAL_INDEX = Path(__file__).resolve().parents[1] / "data/cache/stellarium/v26.3/modern/index.json"


@pytest.fixture
def real_rows():
    if not REAL_INDEX.exists():
        pytest.skip("index.json not fetched; run uv run python -m anser.stellarium_fetch")
    return parse_sky_culture(json.loads(REAL_INDEX.read_text()))


def test_real_file_figure_counts(real_rows):
    by_kind = {}
    for r in real_rows:
        by_kind.setdefault(r["kind"], set()).add(r["figure_id"])
    assert len(by_kind["constellation"]) == 88
    assert len(by_kind["asterism"]) == 81  # 92 minus the 11 ray helpers


def test_real_file_edge_count(real_rows):
    assert len(real_rows) == 1201  # 695 constellation + 506 asterism edges, counted 27 November 2026


def test_real_file_kembles_cascade_is_all_gaia(real_rows):
    rows = rows_for(real_rows, "AST modern TA1")
    assert rows
    assert all(r["star_a"].startswith("gaia_dr3:") and r["star_b"].startswith("gaia_dr3:") for r in rows)


# --- write_figure_edges: rows go to a Parquet file through DuckDB ---

import duckdb  # noqa: E402

from anser.stellarium_parse import write_figure_edges  # noqa: E402

COLUMN_ORDER = ["sky_culture", "figure_id", "kind", "star_a", "star_b"]


def read_back(path):
    rel = duckdb.read_parquet(str(path))
    return rel.columns, rel.types, rel.fetchall()


def test_written_file_has_columns_in_order(tmp_path):
    target = write_figure_edges(parse_sky_culture(FIXTURE), tmp_path / "figure_edge.parquet")
    columns, types, _ = read_back(target)
    assert columns == COLUMN_ORDER
    assert all(str(t) == "VARCHAR" for t in types)


def test_written_file_round_trips(tmp_path):
    rows = parse_sky_culture(FIXTURE)
    target = write_figure_edges(rows, tmp_path / "figure_edge.parquet")
    _, _, back = read_back(target)
    expected = sorted(tuple(r[c] for c in COLUMN_ORDER) for r in rows)
    assert back == expected  # same rows, and the file is sorted


def test_write_leaves_no_partial_file(tmp_path):
    target = write_figure_edges(parse_sky_culture(FIXTURE), tmp_path / "out" / "figure_edge.parquet")
    assert target.exists()
    assert list(target.parent.iterdir()) == [target]


def test_empty_rows_still_write_the_columns(tmp_path):
    target = write_figure_edges([], tmp_path / "figure_edge.parquet")
    columns, _, back = read_back(target)
    assert columns == COLUMN_ORDER
    assert back == []
