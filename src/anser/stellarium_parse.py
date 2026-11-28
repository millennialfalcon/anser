import duckdb
import json
import pyarrow as pa
from pathlib import Path 
from anser.stellarium_fetch import fetch_index

schema = pa.schema([(c, pa.string()) for c in ["sky_culture", "figure_id", "kind", "star_a", "star_b"]])

def normalize_id(raw) -> str: 
    if type(raw) is str: 
        if raw.startswith("DSO:") and len(raw) > 4: 
            return "dso:"+raw[4:] 
        if raw.isdecimal() and raw.isascii(): 
            return f"gaia_dr3:{raw}"

    if type(raw) is int and 0 < raw <= 120416: #hip limit. static. 
        return f"hip:{raw}"

    raise ValueError(f"{raw!r} not a valid id.")

def figure_edges(lines) -> list[tuple[str,str]]: 
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
    edges = pa.Table.from_pylist(rows, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    duckdb.sql(f"""
            COPY (SELECT * FROM edges ORDER BY ALL) TO '{partial}' (FORMAT parquet)
            """)
    partial.replace(path)
    return path 

def build() -> Path: 
    data = json.loads(fetch_index().read_text())
    rows = parse_sky_culture(data)
    return write_figure_edges(rows, fetch_index().parent.parent / "figure_edge.parquet")

if __name__ == "__main__": 
    print(build())