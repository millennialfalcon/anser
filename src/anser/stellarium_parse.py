def normalize_id(raw) -> str: 
    if type(raw) is str: 
        if raw.startswith("DSO:") and len(raw) > 4: 
            return "dso:"+raw[4:] 
        if raw.isdecimal() and raw.isascii(): 
            return f"gaia_dr3:{raw}"

    if type(raw) is int and 0 < raw <= 120416: #hip limit. static. 
        return f"hip:{raw}"

    raise ValueError(f"{raw!r} not a valid id.")
