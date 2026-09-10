"""Synthetic ZIP tests for NPPES ingestion behavior."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src import ingest


MAIN_PROVIDER_FILE = "npidata_pfile_20260101-20260107.csv"


def provider_columns() -> list[str]:
    """Return a minimal valid header using exact documented raw names."""
    return [
        *ingest.RETAINED_BASE_COLUMNS,
        "Healthcare Provider Taxonomy Code_1",
        "Healthcare Provider Primary Taxonomy Switch_1",
    ]


def synthetic_row(**overrides: str) -> dict[str, str]:
    """Build one non-real NPPES-shaped row for a temporary test archive."""
    row = {column: "" for column in provider_columns()}
    row.update(
        {
            "NPI": "1000000001",
            "Entity Type Code": "1",
            "Provider Last Name (Legal Name)": "Synthetic",
            "Provider First Name": "Example",
            "Provider Business Practice Location Address State Name": "MA",
            "Provider Business Practice Location Address Postal Code": "02108",
            "Healthcare Provider Taxonomy Code_1": "207Q00000X",
            "Healthcare Provider Primary Taxonomy Switch_1": "Y",
        }
    )
    row.update(overrides)
    return row


def create_synthetic_zip(
    tmp_path: Path,
    rows: list[dict[str, str]],
    columns: list[str] | None = None,
) -> Path:
    """Create a ZIP containing a tiny synthetic provider CSV and header file."""
    columns = columns or provider_columns()
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(
        [{column: row.get(column, "") for column in columns} for row in rows]
    )

    archive_path = tmp_path / "synthetic_weekly_v2.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(MAIN_PROVIDER_FILE, buffer.getvalue())
        archive.writestr(
            "npidata_pfile_20260101-20260107_fileheader.csv",
            "Synthetic header reference only\n",
        )
    return archive_path


def test_expected_main_provider_csv_is_identified(tmp_path: Path):
    archive_path = create_synthetic_zip(tmp_path, [synthetic_row()])

    with zipfile.ZipFile(archive_path) as archive:
        main_file = ingest.find_main_provider_csv(archive)

    assert main_file.filename == MAIN_PROVIDER_FILE


def test_missing_required_column_has_clear_error(tmp_path: Path):
    columns = [
        column for column in provider_columns() if column != "Provider First Name"
    ]
    row = synthetic_row()
    archive_path = create_synthetic_zip(tmp_path, [row], columns)

    with pytest.raises(ingest.IngestionError, match="Provider First Name"):
        ingest.ingest(archive_path, tmp_path / "bronze", chunk_size=2)


def test_only_massachusetts_rows_are_written(tmp_path: Path):
    archive_path = create_synthetic_zip(
        tmp_path,
        [
            synthetic_row(
                **{
                    "NPI": "1000000001",
                    "Provider Business Practice Location Address State Name": "MA",
                }
            ),
            synthetic_row(
                **{
                    "NPI": "1000000002",
                    "Provider Business Practice Location Address State Name": "NY",
                }
            ),
        ],
    )
    output_dir = tmp_path / "bronze"
    ingest.ingest(archive_path, output_dir, chunk_size=1)

    parquet_path, _ = ingest.output_paths(archive_path, output_dir)
    result = pd.read_parquet(parquet_path)
    states = result[
        "Provider Business Practice Location Address State Name"
    ].str.upper()

    assert len(result) == 1
    assert states.eq("MA").all()


def test_metadata_records_input_and_massachusetts_counts(tmp_path: Path):
    archive_path = create_synthetic_zip(
        tmp_path,
        [
            synthetic_row(**{"NPI": "1000000001"}),
            synthetic_row(**{"NPI": "1000000002"}),
            synthetic_row(
                **{
                    "NPI": "1000000003",
                    "Provider Business Practice Location Address State Name": "CT",
                }
            ),
        ],
    )
    output_dir = tmp_path / "bronze"
    returned_metadata = ingest.ingest(archive_path, output_dir, chunk_size=2)
    parquet_path, metadata_path = ingest.output_paths(archive_path, output_dir)
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert returned_metadata["input_row_count"] == 3
    assert returned_metadata["massachusetts_row_count"] == 2
    assert saved_metadata["source_filename"] == archive_path.name
    assert saved_metadata["input_row_count"] == 3
    assert saved_metadata["massachusetts_row_count"] == 2
    assert saved_metadata["output_filename"] == parquet_path.name
    assert (
        len(pd.read_parquet(parquet_path)) == saved_metadata["massachusetts_row_count"]
    )
