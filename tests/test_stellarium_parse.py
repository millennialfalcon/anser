"""Tests for parsing Stellarium's index.json into figure edges."""

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
