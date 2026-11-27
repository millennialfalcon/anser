import requests
from pathlib import Path

stellarium_tag = "v26.3"
url = f"https://raw.githubusercontent.com/Stellarium/stellarium/{stellarium_tag}/skycultures/modern/index.json"
root = Path(__file__).resolve().parents[2]
path = root / "data" / "cache" / "stellarium" / stellarium_tag / "modern" / "index.json"

def fetch_index(path:Path=path, *, force:bool=False) -> Path: 
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