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