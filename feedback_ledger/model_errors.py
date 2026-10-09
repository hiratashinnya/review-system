"""Parsing error type for feedback ledger documents."""

class DocumentError(Exception):
    """TOML として読めない（構文エラー）。"""
