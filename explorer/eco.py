"""Opening-name lookup against the bundled Lichess ECO database
(data/eco.tsv), keyed by exact SAN move prefix. Loaded once and cached."""

import os
from functools import lru_cache

from django.conf import settings


def _eco_path():
    return os.path.join(settings.BASE_DIR, "data", "eco.tsv")


@lru_cache(maxsize=1)
def _load_index():
    index = {}

    path = _eco_path()
    if not os.path.exists(path):
        return index

    with open(path, "r", encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            eco, name, pgn = parts
            moves = [tok for tok in pgn.split() if not tok.endswith(".")]
            if not moves:
                continue
            index.setdefault(tuple(moves), (eco, name))

    return index


def lookup(move_path):
    """Return (eco, name) for an exact SAN move sequence, or None."""
    return _load_index().get(tuple(move_path))
