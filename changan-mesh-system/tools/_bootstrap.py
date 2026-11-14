"""Allow administrative scripts to run under IDF Python as well as uv."""
from pathlib import Path
import sys
def bootstrap():
    path=str(Path(__file__).resolve().parents[1]/"host/src")
    if path not in sys.path: sys.path.insert(0,path)
