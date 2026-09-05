"""File parsing for the import pipeline. Supports .csv, .xlsx, .xls.

Returns headers + rows as plain Python types (no pandas/numpy objects) so
the result is directly JSON-serializable for caching on the DataImportJob
row between wizard steps.
"""
import io

import pandas as pd


class UnsupportedFileTypeError(Exception):
    pass


def parse_upload(filename: str, content: bytes) -> tuple[list[str], list[dict]]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False)
    else:
        raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")

    df = df.dropna(how="all")
    headers = [str(c).strip() for c in df.columns]
    df.columns = headers
    rows = df.to_dict(orient="records")
    return headers, rows
