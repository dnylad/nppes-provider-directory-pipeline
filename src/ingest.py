"""Stream a weekly NPPES provider ZIP into a Massachusetts Parquet subset.

This module intentionally performs only ingestion and geography filtering.
Primary-care cohort filtering and other business transformations belong in a
later pipeline step.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


LOGGER = logging.getLogger(__name__)

NPI = "NPI"
ENTITY_TYPE = "Entity Type Code"
PRACTICE_STATE = "Provider Business Practice Location Address State Name"
PRACTICE_ZIP = "Provider Business Practice Location Address Postal Code"

# These are the non-repeating columns required by docs/data_contract.md for
# Version 1 processing. Taxonomy columns are validated separately because the
# source can contain multiple numbered slots.
REQUIRED_CORE_COLUMNS = (
    NPI,
    ENTITY_TYPE,
    "Provider Last Name (Legal Name)",
    "Provider First Name",
    PRACTICE_STATE,
    PRACTICE_ZIP,
)

# Retain all fields needed by later provider, taxonomy, and address-quality
# transformations. Every present taxonomy code and matching primary switch is
# appended after the source header is inspected.
RETAINED_BASE_COLUMNS = (
    NPI,
    ENTITY_TYPE,
    "Replacement NPI",
    "Provider Organization Name (Legal Business Name)",
    "Provider Last Name (Legal Name)",
    "Provider First Name",
    "Provider Middle Name",
    "Provider Name Prefix Text",
    "Provider Name Suffix Text",
    "Provider Credential Text",
    "Provider First Line Business Practice Location Address",
    "Provider Second Line Business Practice Location Address",
    "Provider Business Practice Location Address City Name",
    PRACTICE_STATE,
    PRACTICE_ZIP,
    "Provider Business Practice Location Address Country Code (If outside U.S.)",
    "Provider Business Practice Location Address Telephone Number",
    "Provider Business Practice Location Address Fax Number",
    "Provider Enumeration Date",
    "Last Update Date",
    "NPI Deactivation Reason Code",
    "NPI Deactivation Date",
    "NPI Reactivation Date",
)

TAXONOMY_CODE_PREFIX = "Healthcare Provider Taxonomy Code_"
PRIMARY_TAXONOMY_PREFIX = "Healthcare Provider Primary Taxonomy Switch_"


class IngestionError(Exception):
    """An expected input problem, phrased for a command-line user."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stream the main NPPES provider CSV from a ZIP and write a "
            "Massachusetts primary-practice-location Parquet subset."
        )
    )
    parser.add_argument("input_zip", type=Path, help="Path to an NPPES weekly ZIP file.")
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory for the generated Parquet file and JSON metadata.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
        help="Rows to read at a time (default: 100000).",
    )
    args = parser.parse_args(argv)
    if args.chunk_size < 1:
        parser.error("--chunk-size must be a positive whole number.")
    return args


def find_main_provider_csv(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    """Return the one main provider CSV, excluding header/reference CSVs."""
    candidates = [
        entry
        for entry in archive.infolist()
        if entry.filename.rsplit("/", 1)[-1].startswith("npidata_pfile_")
        and entry.filename.lower().endswith(".csv")
        and not entry.filename.lower().endswith("_fileheader.csv")
    ]
    if not candidates:
        raise IngestionError(
            "Could not find the main provider CSV (expected a file named "
            "like 'npidata_pfile_YYYYMMDD-YYYYMMDD.csv') inside the ZIP."
        )
    if len(candidates) > 1:
        names = ", ".join(entry.filename for entry in candidates)
        raise IngestionError(
            "Found more than one possible main provider CSV in the ZIP: "
            f"{names}. Please supply an archive containing one weekly provider file."
        )
    return candidates[0]


def taxonomy_columns(columns: Sequence[str]) -> tuple[list[str], list[str]]:
    """Find numbered taxonomy fields and require their matching switch fields."""
    code_columns = sorted(
        (column for column in columns if column.startswith(TAXONOMY_CODE_PREFIX)),
        key=lambda column: int(column.removeprefix(TAXONOMY_CODE_PREFIX)),
    )
    if not code_columns:
        raise IngestionError(
            "The provider CSV does not contain any 'Healthcare Provider Taxonomy Code_*' columns."
        )

    available = set(columns)
    switch_columns: list[str] = []
    missing_switches: list[str] = []
    for code_column in code_columns:
        slot = code_column.removeprefix(TAXONOMY_CODE_PREFIX)
        switch_column = f"{PRIMARY_TAXONOMY_PREFIX}{slot}"
        if switch_column in available:
            switch_columns.append(switch_column)
        else:
            missing_switches.append(switch_column)

    if missing_switches:
        raise IngestionError(
            "The provider CSV is missing the primary-taxonomy field(s) paired "
            f"with its taxonomy code field(s): {', '.join(missing_switches)}."
        )
    return code_columns, switch_columns


def retained_columns_from_header(columns: Sequence[str]) -> list[str]:
    """Validate contract fields and return source-order columns to keep."""
    available = set(columns)
    missing = [column for column in REQUIRED_CORE_COLUMNS if column not in available]
    if missing:
        raise IngestionError(
            "The provider CSV is missing required column(s) from docs/data_contract.md: "
            + ", ".join(missing)
        )

    code_columns, switch_columns = taxonomy_columns(columns)
    retained = [column for column in RETAINED_BASE_COLUMNS if column in available]
    retained.extend(code_columns)
    retained.extend(switch_columns)
    # Preserve the exact input order and avoid accidental duplicate selections.
    retained_set = set(retained)
    return [column for column in columns if column in retained_set]


def output_paths(input_zip: Path, output_dir: Path) -> tuple[Path, Path]:
    stem = input_zip.stem
    return (
        output_dir / f"{stem}_massachusetts.parquet",
        output_dir / f"{stem}_massachusetts_metadata.json",
    )


def ingest(input_zip: Path, output_dir: Path, chunk_size: int) -> dict[str, object]:
    """Ingest an NPPES ZIP and return metadata for the generated outputs."""
    if not input_zip.is_file():
        raise IngestionError(
            f"Input ZIP not found: {input_zip}. Check the path and try again."
        )
    if input_zip.suffix.lower() != ".zip":
        raise IngestionError(f"Input must be a .zip file, not: {input_zip.name}")

    try:
        with zipfile.ZipFile(input_zip) as archive:
            main_csv = find_main_provider_csv(archive)
            with archive.open(main_csv) as header_stream:
                header = pd.read_csv(header_stream, nrows=0, dtype=str).columns.tolist()
            retained_columns = retained_columns_from_header(header)

            output_dir.mkdir(parents=True, exist_ok=True)
            parquet_path, metadata_path = output_paths(input_zip, output_dir)
            temporary_parquet = parquet_path.with_suffix(".parquet.tmp")
            input_row_count = 0
            massachusetts_row_count = 0
            parquet_schema = pa.schema(
                [pa.field(column, pa.string()) for column in retained_columns]
            )
            writer = pq.ParquetWriter(temporary_parquet, parquet_schema)

            LOGGER.info("Reading %s from %s in chunks of %s rows.", main_csv.filename, input_zip.name, chunk_size)
            try:
                with archive.open(main_csv) as csv_stream:
                    for chunk_number, chunk in enumerate(
                        pd.read_csv(
                            csv_stream,
                            usecols=retained_columns,
                            dtype=str,
                            chunksize=chunk_size,
                            keep_default_na=False,
                        ),
                        start=1,
                    ):
                        input_row_count += len(chunk)
                        ma_chunk = chunk.loc[
                            chunk[PRACTICE_STATE].str.strip().str.upper().eq("MA")
                        ]
                        massachusetts_row_count += len(ma_chunk)

                        if not ma_chunk.empty:
                            writer.write_table(
                                pa.Table.from_pandas(
                                    ma_chunk,
                                    schema=parquet_schema,
                                    preserve_index=False,
                                )
                            )
                        LOGGER.info(
                            "Processed chunk %s: %s input rows, %s Massachusetts rows so far.",
                            chunk_number,
                            input_row_count,
                            massachusetts_row_count,
                        )

            finally:
                writer.close()

            temporary_parquet.replace(parquet_path)
            metadata: dict[str, object] = {
                "source_filename": input_zip.name,
                "run_time_utc": datetime.now(timezone.utc).isoformat(),
                "input_row_count": input_row_count,
                "massachusetts_row_count": massachusetts_row_count,
                "output_filename": parquet_path.name,
                "retained_columns": retained_columns,
            }
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    except zipfile.BadZipFile as error:
        raise IngestionError(
            f"Could not read '{input_zip.name}' as a ZIP file. Download it again and retry."
        ) from error
    except pd.errors.ParserError as error:
        raise IngestionError(
            "The main provider CSV could not be parsed. Confirm that the ZIP contains "
            "an unmodified NPPES Version 2 provider file."
        ) from error

    LOGGER.info(
        "Finished ingestion: %s of %s rows have a Massachusetts primary practice location. Output: %s",
        massachusetts_row_count,
        input_row_count,
        parquet_path,
    )
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        ingest(args.input_zip, args.output_dir, args.chunk_size)
    except IngestionError as error:
        LOGGER.error("Ingestion stopped: %s", error)
        return 2
    except (OSError, PermissionError) as error:
        LOGGER.error("Ingestion stopped because a file could not be read or written: %s", error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
