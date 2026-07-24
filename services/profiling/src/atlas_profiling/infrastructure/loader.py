"""Load tabular datasets into pandas for profiling."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd


def load_dataframe(data: bytes, filename: str, *, max_rows: int | None = 1_000_000) -> pd.DataFrame:
    """Load supported formats; optionally cap rows for memory safety."""
    name = filename.lower()
    bio = io.BytesIO(data)
    if name.endswith(".csv"):
        df = pd.read_csv(bio, nrows=max_rows)
    elif name.endswith(".tsv"):
        df = pd.read_csv(bio, sep="\t", nrows=max_rows)
    elif name.endswith(".json"):
        df = pd.read_json(bio)
        if max_rows is not None:
            df = df.head(max_rows)
    elif name.endswith(".parquet"):
        df = pd.read_parquet(bio)
        if max_rows is not None:
            df = df.head(max_rows)
    elif name.endswith(".xlsx"):
        df = pd.read_excel(bio, nrows=max_rows)
    else:
        # try CSV fallback
        bio.seek(0)
        df = pd.read_csv(bio, nrows=max_rows)
    return df


def load_dataframe_from_path(path: Path, *, max_rows: int | None = 1_000_000) -> pd.DataFrame:
    return load_dataframe(path.read_bytes(), path.name, max_rows=max_rows)
