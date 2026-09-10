"""Load Silver NPPES Parquet files into a local Gold DuckDB analytics database."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

import duckdb


LOGGER = logging.getLogger(__name__)

SOURCE_FILES = {
    "providers": "providers_ma_primary_care.parquet",
    "provider_taxonomies": "provider_taxonomies.parquet",
}
MODELS_PATH = Path(__file__).resolve().parent.parent / "sql" / "gold" / "models.sql"


class LoadError(Exception):
    """An expected loading problem, phrased for a command-line user."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or refresh a local Gold DuckDB warehouse from Silver NPPES Parquet files."
        )
    )
    parser.add_argument(
        "processed_dir",
        type=Path,
        help="Silver directory containing providers_ma_primary_care.parquet and provider_taxonomies.parquet.",
    )
    parser.add_argument(
        "database_path",
        type=Path,
        help="Path for the local Gold DuckDB database, normally under data/gold/.",
    )
    return parser.parse_args(argv)


def sql_path_literal(path: Path) -> str:
    """Return an absolute Windows-safe SQL string literal for a local path."""
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def validate_sources(processed_dir: Path) -> dict[str, Path]:
    if not processed_dir.is_dir():
        raise LoadError(
            f"Silver-data directory not found: {processed_dir}. Run src/transform.py first."
        )

    sources = {table: processed_dir / filename for table, filename in SOURCE_FILES.items()}
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise LoadError(
            "Required Silver Parquet file(s) are missing: " + ", ".join(missing)
        )
    return sources


def source_row_count(connection: duckdb.DuckDBPyConnection, parquet_path: Path) -> int:
    path = sql_path_literal(parquet_path)
    return int(connection.execute(f"SELECT COUNT(*) FROM read_parquet('{path}')").fetchone()[0])


def load_table(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    parquet_path: Path,
) -> tuple[int, int]:
    """Replace a table from Parquet and return source and loaded row counts."""
    path = sql_path_literal(parquet_path)
    source_count = source_row_count(connection, parquet_path)
    connection.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')"
    )
    loaded_count = int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    LOGGER.info("Loaded %s: %s source rows, %s table rows.", table_name, source_count, loaded_count)
    if source_count != loaded_count:
        raise LoadError(
            f"Row-count validation failed for '{table_name}': expected {source_count}, "
            f"but loaded {loaded_count}. The database was not left as a trusted refresh."
        )
    return source_count, loaded_count


def apply_models(connection: duckdb.DuckDBPyConnection) -> None:
    if not MODELS_PATH.is_file():
        raise LoadError(f"SQL view file not found: {MODELS_PATH}")
    try:
        connection.execute(MODELS_PATH.read_text(encoding="utf-8"))
    except OSError as error:
        raise LoadError(f"Could not read SQL view file '{MODELS_PATH}': {error}") from error
    LOGGER.info("Created or replaced analytics views from %s.", MODELS_PATH.name)


def load(processed_dir: Path, database_path: Path) -> dict[str, tuple[int, int]]:
    """Refresh Gold warehouse tables and views, returning validated row counts."""
    sources = validate_sources(processed_dir)
    if database_path.exists() and database_path.is_dir():
        raise LoadError(f"Database path is a directory, not a file: {database_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        connection = duckdb.connect(str(database_path))
    except duckdb.Error as error:
        raise LoadError(f"Could not open DuckDB database '{database_path}': {error}") from error

    try:
        results = {
            table_name: load_table(connection, table_name, parquet_path)
            for table_name, parquet_path in sources.items()
        }
        apply_models(connection)
    except duckdb.Error as error:
        raise LoadError(f"DuckDB could not complete the load: {error}") from error
    finally:
        connection.close()

    LOGGER.info("Warehouse refresh completed: %s", database_path)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        load(args.processed_dir, args.database_path)
    except LoadError as error:
        LOGGER.error("Load stopped: %s", error)
        return 2
    except OSError as error:
        LOGGER.error("Load stopped because a file could not be read or written: %s", error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
