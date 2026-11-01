"""SQL guard: only a single read-only SELECT reaches the database, with a row cap.

Defence in depth: the warehouse connection also has external access disabled and its
configuration locked (see warehouse.py), so the guard is the first of two walls.
"""
from __future__ import annotations

import re

import duckdb

MAX_ROWS = 1000

# Functions and keywords that read files, reach the network, change state or settings.
_DENY = re.compile(
    r"\b("
    r"read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|parquet_scan|csv_scan|json_scan|"
    r"glob|sniff_csv|copy|export|import|attach|detach|install|load|pragma|set|reset|call|"
    r"create|insert|update|delete|drop|alter|truncate|replace|merge|grant|revoke|vacuum|checkpoint|"
    r"getenv|current_setting|duckdb_settings|duckdb_secrets|http\w*|s3|httpfs|system"
    r")\b",
    re.IGNORECASE,
)
_FILE_LITERAL = re.compile(r"'[^']*\.(csv|tsv|parquet|json|ndjson|txt|db|duckdb|sqlite)'", re.IGNORECASE)
_ALLOWED_START = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


class UnsafeSQL(ValueError):
    """Raised when SQL is not a single read-only SELECT."""


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def validate(sql: str) -> str:
    """Return a row-capped, safe version of `sql`, or raise UnsafeSQL."""
    if not sql or not sql.strip():
        raise UnsafeSQL("Empty query.")
    clean = _strip_comments(sql).strip().rstrip(";").strip()
    try:
        statements = duckdb.extract_statements(clean)
    except duckdb.Error as exc:
        raise UnsafeSQL(f"Query does not parse: {exc}") from exc
    if len(statements) != 1:
        raise UnsafeSQL("Exactly one statement is allowed.")
    if statements[0].type != duckdb.StatementType.SELECT:
        raise UnsafeSQL("Only SELECT queries are allowed.")
    if not _ALLOWED_START.match(clean):
        raise UnsafeSQL("Query must start with SELECT or WITH.")
    # Check the text outside string literals, so a value like 'delete' in a WHERE is fine.
    outside_strings = re.sub(r"'(?:[^']|'')*'", "''", clean)
    if re.search(r"\b(from|join)\s*\(?\s*'", clean, re.IGNORECASE) or _FILE_LITERAL.search(clean):
        raise UnsafeSQL("Reading files by path is not allowed.")
    hit = _DENY.search(outside_strings)
    if hit:
        raise UnsafeSQL(f"Keyword or function not allowed: {hit.group(0)}")
    return f"SELECT * FROM (\n{clean}\n) AS guarded_query LIMIT {MAX_ROWS}"
