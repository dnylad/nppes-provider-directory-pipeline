"""Synthetic tests for aggregate-only snapshot run manifests."""

from __future__ import annotations

import hashlib
import json

from src import run_manifest


def test_manifest_records_lineage_paths_and_aggregate_counts(tmp_path, monkeypatch):
    source_zip = tmp_path / "synthetic_weekly.zip"
    source_zip.write_bytes(b"synthetic ZIP content only")
    bronze_dir = tmp_path / "bronze" / "snapshot_01"
    silver_dir = tmp_path / "silver" / "snapshot_01"
    manifest_dir = tmp_path / "gold" / "manifests"
    bronze_dir.mkdir(parents=True)
    silver_dir.mkdir(parents=True)

    (bronze_dir / "synthetic_weekly_massachusetts_metadata.json").write_text(
        json.dumps(
            {
                "source_filename": source_zip.name,
                "input_row_count": 12,
                "massachusetts_row_count": 5,
                "output_filename": "synthetic_weekly_massachusetts.parquet",
            }
        ),
        encoding="utf-8",
    )
    (silver_dir / "transform_data_quality_report.json").write_text(
        json.dumps(
            {
                "input_row_count": 5,
                "organization_records_excluded": 1,
                "non_massachusetts_records_excluded": 0,
                "primary_care_providers_retained": 3,
                "missing_npi_count": 0,
                "invalid_npi_count": 0,
                "invalid_enumeration_date_count": 0,
                "invalid_deactivation_date_count": 0,
                "invalid_reactivation_date_count": 0,
                "missing_zip_count": 1,
                "missing_taxonomy_count": 0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_manifest, "git_commit_sha", lambda _: "synthetic-commit")

    manifest_path = run_manifest.write_manifest(
        "snapshot_01",
        source_zip,
        bronze_dir,
        silver_dir,
        tmp_path / "gold" / "nppes.duckdb",
        manifest_dir,
        repository_root=tmp_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest_path == manifest_dir / "snapshot_01.json"
    assert manifest["snapshot_label"] == "snapshot_01"
    assert manifest["source_zip_filename"] == "synthetic_weekly.zip"
    assert (
        manifest["source_zip_sha256"]
        == hashlib.sha256(source_zip.read_bytes()).hexdigest()
    )
    assert manifest["git_commit_sha"] == "synthetic-commit"
    assert manifest["bronze_counts"] == {
        "input_row_count": 12,
        "massachusetts_row_count": 5,
    }
    assert (
        manifest["silver_data_quality_counts"]["primary_care_providers_retained"] == 3
    )
    assert manifest["silver_data_quality_counts"]["missing_zip_count"] == 1
    assert manifest["output_paths"]["bronze_directory"] == str(bronze_dir)
    assert "npi" not in manifest
    assert "provider_name" not in manifest
