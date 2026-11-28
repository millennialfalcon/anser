"""Parse Stellarium's sky culture file into the ``figure_edge`` table.

Each figure in ``index.json`` is a list of polylines: ``[a, b, c]`` draws the
segments a-b and b-c. This module turns them into one row per edge, with
namespaced star IDs, and writes the rows to Parquet.

Build the real table from the repo root::

    uv run python -m anser.stellarium_parse

It lands at ``data/cache/stellarium/<tag>/figure_edge.parquet``.
"""

import duckdb
import json
import pyarrow as pa
from pathlib import Path
from anser.stellarium_fetch import fetch_index

# figure_edge's columns, in file order. All strings.
#   sky_culture  Stellarium's sky culture ID, e.g. "modern"
#   figure_id    Stellarium's figure ID, e.g. "AST modern CoH". Sprint 3
#                maps these to minted concept IDs.
#   kind         "constellation" or "asterism"
#   star_a       the edge's two ends as namespaced IDs, sorted so that
#   star_b       star_a < star_b
schema = pa.schema([(c, pa.string()) for c in ["sky_culture", "figure_id", "kind", "star_a", "star_b"]])

def normalize_id(raw) -> str:
    """Turn one point from a Stellarium line into a namespaced ID.

    - A positive int up to 120416 is a Hipparcos number: ``95771`` becomes
      ``"hip:95771"``. The Hipparcos catalog is closed, so the bound is fixed.
    - An all-digit ASCII string is a Gaia DR3 source ID: ``"535...880"``
      becomes ``"gaia_dr3:535...880"``. Gaia IDs are strings in the JSON
      because they run past 2**53, where JSON numbers lose digits.
    - ``"DSO:<name>"`` is a deep-sky object, not a star: ``"DSO:IC2602"``
      becomes ``"dso:IC2602"``.

    Raises:
        ValueError: Anything else, including bools, floats, 0 and negatives.
    """
    if type(raw) is str:
        if raw.startswith("DSO:") and len(raw) > 4: 
            return "dso:"+raw[4:] 
        if raw.isdecimal() and raw.isascii(): 
            return f"gaia_dr3:{raw}"

    if type(raw) is int and 0 < raw <= 120416: # highest HIP number; the catalog is closed
        return f"hip:{raw}"

    raise ValueError(f"{raw!r} not a valid id.")

def figure_edges(lines) -> list[tuple[str,str]]:
    """Turn one figure's polylines into its edges.

    Args:
        lines: The figure's ``lines`` value, a list of polylines, each a list
            of raw points. A closed loop repeats its first point at the end.

    Returns:
        Sorted, deduplicated ``(star_a, star_b)`` pairs of namespaced IDs,
        each pair sorted so a-b and b-a are the same edge. The sort is on
        strings, so ``"hip:100"`` comes before ``"hip:99"``.

    Raises:
        ValueError: A line has fewer than two points, a point isn't a valid
            ID, or a segment joins a star to itself.
    """
    edges = set()
    for line in lines: 
        line = [normalize_id(x) for x in line]
        if len(line) < 2: 
            raise ValueError(f"Edge needs at least two stars, got {line!r}")
        for i, j in zip(line, line[1:]): 
            if i != j: 
                edges.add(tuple(sorted((i,j)))) 
            else: 
                raise ValueError(f"{i} identified as sharing an edge with itself")
    return sorted(edges)

def parse_sky_culture(data:dict) -> list[dict]:
    """Turn a loaded ``index.json`` into ``figure_edge`` rows.

    Reads both ``constellations`` and ``asterisms``. Skips the unnamed ray
    helpers (figures flagged ``is_ray_helper``), which are pointer arcs
    between patterns rather than patterns. Ignores the top-level ``edges``
    key, which holds IAU constellation boundaries, not figure lines. Does not
    modify ``data``.

    Args:
        data: The parsed JSON, e.g. ``json.loads(fetch_index().read_text())``.

    Returns:
        One dict per edge, with the five keys in ``schema``.

    Raises:
        ValueError: A figure has a bad line; the message starts with its ID.
    """
    sky_culture = data["id"]
    rows = []
    
    for kind, patterns in [("asterism", data["asterisms"]), ("constellation", data["constellations"])]: 
        for pattern in patterns: 
            if pattern.get("is_ray_helper") is not None: 
                continue 
            figure_id = pattern["id"]
            try: 
                edges = figure_edges(pattern["lines"])
            except ValueError as e: 
                raise ValueError(f"{pattern['id']}: {e}") from e
            for i, j in edges: 
                rows.append(
                    {
                        "sky_culture" : sky_culture,
                        "kind" : kind, 
                        "figure_id" : figure_id, 
                        "star_a" : i, 
                        "star_b" : j
                    }
                )
    return rows

def write_figure_edges(rows:list[dict], path:Path) -> Path:
    """Write ``figure_edge`` rows to a Parquet file, replacing any old one.

    The rows go through DuckDB, which reads the local Arrow table ``edges`` by
    name and sorts by every column, so the same rows always make the same
    file. Like the fetch, it writes a ``.part`` file and renames it at the
    end. An empty ``rows`` still writes the five columns.

    Returns:
        ``path``.
    """
    edges = pa.Table.from_pylist(rows, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    duckdb.sql(f"""
            COPY (SELECT * FROM edges ORDER BY ALL) TO '{partial}' (FORMAT parquet)
            """)
    partial.replace(path)
    return path 

def build() -> Path:
    """Fetch (if needed), parse and write the real table. Returns its path."""
    data = json.loads(fetch_index().read_text())
    rows = parse_sky_culture(data)
    return write_figure_edges(rows, fetch_index().parent.parent / "figure_edge.parquet")

if __name__ == "__main__": 
    print(build())