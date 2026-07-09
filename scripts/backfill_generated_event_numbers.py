"""Backfill generated event numbers for existing Peace/Protective Order ESRI rows.

This script updates only rows in dbo.esri_events where:
- generated_event_number is NULL
- event_number is NULL/blank
- activity_type contains "peace" or "protective"

It uses the same allocator as live webhook ingestion so the existing monthly
sequence table remains the source of truth.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db import allocate_generated_event_number, get_conn

DEFAULT_TABLE = "dbo.esri_events"
DEFAULT_SEQUENCE_TABLE = "dbo.daily_log_event_number_sequences"
DEFAULT_BATCH_SIZE = 500
DEFAULT_CONNECTION_STRING_ENV = "AZURE_SQL_CONNECTION_STRING"


def _quote_identifier_part(identifier: str) -> str:
    if not identifier or "]" in identifier:
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f"[{identifier}]"


def quote_table_name(table_name: str) -> str:
    parts = table_name.split(".")
    if len(parts) not in (1, 2) or any(not part for part in parts):
        raise ValueError(f"Invalid SQL table name: {table_name!r}")
    return ".".join(_quote_identifier_part(part) for part in parts)


def find_single_column_primary_key(cur, table_name: str) -> str | None:
    parts = table_name.split(".")
    if len(parts) == 2:
        schema_name, object_name = parts
    else:
        schema_name, object_name = "dbo", parts[0]

    cur.execute(
        """
        SELECT c.name
        FROM sys.key_constraints kc
        JOIN sys.index_columns ic
            ON kc.parent_object_id = ic.object_id
            AND kc.unique_index_id = ic.index_id
        JOIN sys.columns c
            ON ic.object_id = c.object_id
            AND ic.column_id = c.column_id
        JOIN sys.tables t
            ON kc.parent_object_id = t.object_id
        JOIN sys.schemas s
            ON t.schema_id = s.schema_id
        WHERE kc.type = 'PK'
            AND s.name = ?
            AND t.name = ?
        ORDER BY ic.key_ordinal;
        """,
        schema_name,
        object_name,
    )
    columns = [row[0] for row in cur.fetchall()]
    if len(columns) == 1:
        return columns[0]
    return None


def build_backfill_select_sql(table_name: str, key_column: str) -> str:
    table = quote_table_name(table_name)
    key = _quote_identifier_part(key_column)
    return f"""
    SELECT TOP (?) {key}, arrival_time
    FROM {table} WITH (UPDLOCK, READPAST, ROWLOCK)
    WHERE generated_event_number IS NULL
        AND (event_number IS NULL OR LTRIM(RTRIM(event_number)) = '')
        AND (
            LOWER(COALESCE(activity_type, '')) LIKE '%peace%'
            OR LOWER(COALESCE(activity_type, '')) LIKE '%protective%'
        )
    ORDER BY arrival_time, {key};
    """


def build_backfill_update_sql(table_name: str, key_column: str) -> str:
    table = quote_table_name(table_name)
    key = _quote_identifier_part(key_column)
    return f"""
    UPDATE {table}
        SET generated_event_number = ?
        WHERE {key} = ?
            AND generated_event_number IS NULL
            AND (event_number IS NULL OR LTRIM(RTRIM(event_number)) = '')
            AND (
                LOWER(COALESCE(activity_type, '')) LIKE '%peace%'
                OR LOWER(COALESCE(activity_type, '')) LIKE '%protective%'
            );
    """


def backfill_generated_event_numbers(batch_size: int, key_column: str | None, dry_run: bool) -> int:
    total_updated = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            if key_column is None:
                key_column = find_single_column_primary_key(cur, DEFAULT_TABLE)
                if key_column is None:
                    raise RuntimeError(
                        "Could not auto-detect a single-column primary key for dbo.esri_events. "
                        "Re-run with --key-column <column_name>."
                    )
                logging.info("Auto-detected dbo.esri_events primary key column: %s", key_column)

            select_sql = build_backfill_select_sql(DEFAULT_TABLE, key_column)
            update_sql = build_backfill_update_sql(DEFAULT_TABLE, key_column)

            while True:
                cur.execute(select_sql, batch_size)
                rows = cur.fetchall()
                if not rows:
                    conn.commit()
                    break

                for row in rows:
                    row_key = row[0]
                    arrival_time = row[1]
                    generated_event_number = allocate_generated_event_number(cur, arrival_time)

                    if dry_run:
                        logging.info(
                            "DRY RUN: would set generated_event_number=%s for %s=%s",
                            generated_event_number,
                            key_column,
                            row_key,
                        )
                        continue

                    cur.execute(update_sql, generated_event_number, row_key)
                    if cur.rowcount != 1:
                        raise RuntimeError(
                            f"Expected to update one row for {key_column}={row_key}; updated {cur.rowcount}"
                        )
                    total_updated += 1

                if dry_run:
                    conn.rollback()
                    break

                conn.commit()
                logging.info("Backfilled %s rows so far", total_updated)

    return total_updated


def apply_connection_string_env(connection_string_env: str) -> None:
    """Allow one-off runs to use a differently named local connection-string variable."""
    if connection_string_env == DEFAULT_CONNECTION_STRING_ENV:
        return

    connection_string = os.environ.get(connection_string_env)
    if not connection_string:
        raise RuntimeError(
            f"Environment variable {connection_string_env!r} is not set. "
            f"Set it first or pass a different --connection-string-env value."
        )

    os.environ[DEFAULT_CONNECTION_STRING_ENV] = connection_string


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill dbo.esri_events.generated_event_number for existing Peace/Protective Order rows."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows to process per transaction batch. Default: {DEFAULT_BATCH_SIZE}",
    )
    parser.add_argument(
        "--key-column",
        help="Primary key column on dbo.esri_events. If omitted, a single-column PK is auto-detected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Allocate and log candidate numbers, then roll back without updating rows.",
    )
    parser.add_argument(
        "--connection-string-env",
        default=DEFAULT_CONNECTION_STRING_ENV,
        help=(
            "Environment variable that contains the Azure SQL connection string. "
            f"Default: {DEFAULT_CONNECTION_STRING_ENV}"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")

    apply_connection_string_env(args.connection_string_env)

    updated = backfill_generated_event_numbers(
        batch_size=args.batch_size,
        key_column=args.key_column,
        dry_run=args.dry_run,
    )
    logging.info("Backfill complete. Rows updated: %s", updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
