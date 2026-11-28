"""Download Stellarium's modern sky culture file, pinned to one release.

Stellarium (25.1 and later) keeps each sky culture's figures in one
``index.json``. The file is GPL-licensed, so it is fetched into the ignored
``data/cache/`` folder on demand rather than committed.

Run from the repo root::

    uv run python -m anser.stellarium_fetch
"""

import requests
from pathlib import Path

# The Stellarium release to read. The tag is also part of the cache path, so
# bumping it downloads the new file instead of reusing the old one.
stellarium_tag = "v26.3"
url = f"https://raw.githubusercontent.com/Stellarium/stellarium/{stellarium_tag}/skycultures/modern/index.json"
# src/anser/stellarium_fetch.py -> parents[2] is the repo root.
root = Path(__file__).resolve().parents[2]
path = root / "data" / "cache" / "stellarium" / stellarium_tag / "modern" / "index.json"

def fetch_index(path:Path=path, *, force:bool=False) -> Path:
    """Return the path to ``index.json``, downloading it first if it isn't cached.

    Args:
        path: Where the file lives. Defaults to the pinned cache path.
        force: Download again even if the file already exists.

    Returns:
        The path to the cached file.

    Raises:
        requests.HTTPError: The download came back with an error status.
        requests.RequestException: The download failed to connect or timed out.

    The download goes to a ``.part`` file that is renamed only once it is
    fully written, so an interrupted run never leaves a half file that the
    cache check would trust.
    """
    if path.exists() and not force:
        return path 
    r = requests.get(url, timeout=30)
    r.raise_for_status() 
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    partial.write_bytes(r.content)
    partial.replace(path)
    return path 

if __name__ == "__main__": 
    print(fetch_index())