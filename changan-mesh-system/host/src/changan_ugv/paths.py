"""Repository-local defaults; secrets/runtime may be supplied explicitly by the caller."""
from pathlib import Path
def repository_root():
    return Path(__file__).resolve().parents[3]
