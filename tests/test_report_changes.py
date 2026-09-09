"""Synthetic snapshot tests for aggregate NPPES change reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src import report_changes


def providers(rows: list[dict[str, str]]) -> pd.DataFrame:
    """Build a tiny non-real processed provider snapshot."""
    return pd.DataFrame(rows, columns=["npi", "status", "deactivation_date", "practice_zip"])


def taxonomies(rows: list[dict[str, str]]) -> pd.DataFrame:
    """Build a tiny non-real processed taxonomy snapshot."""
    return pd.DataFrame(rows, columns=["npi", "taxonomy_code"])


def write_snapshot(tmp_path: Path, label: str, provider_rows, taxonomy_rows) -> tuple[Path, Path]:
    provider_path = tmp_path / f"{label}_providers.parquet"
    taxonomy_path = tmp_path / f"{label}_taxonomies.parquet"
    providers(provider_rows).to_parquet(provider_path, index=False)
    taxonomies(taxonomy_rows).to_parquet(taxonomy_path, index=False)
    return provider_path, taxonomy_path


def test_change_report_uses_cautious_aggregate_snapshot_terms(tmp_path: Path):
    old_provider_path, old_taxonomy_path = write_snapshot(
        tmp_path,
        "old",
        [
            {"npi": "1000000001", "status": "active", "deactivation_date": "", "practice_zip": "02101"},
            {"npi": "1000000002", "status": "active", "deactivation_date": "", "practice_zip": "02102"},
            {"npi": "1000000003", "status": "active", "deactivation_date": "", "practice_zip": "02103"},
        ],
        [
            {"npi": "1000000001", "taxonomy_code": "207Q00000X"},
            {"npi": "1000000002", "taxonomy_code": "207R00000X"},
            {"npi": "1000000003", "taxonomy_code": "208000000X"},
        ],
    )
    new_provider_path, new_taxonomy_path = write_snapshot(
        tmp_path,
        "new",
        [
            {"npi": "1000000001", "status": "active", "deactivation_date": "", "practice_zip": "02101"},
            {"npi": "1000000002", "status": "deactivated", "deactivation_date": "2025-01-02", "practice_zip": "02199"},
            {"npi": "1000000004", "status": "active", "deactivation_date": "", "practice_zip": "02201"},
        ],
        [
            {"npi": "1000000001", "taxonomy_code": "207Q00000X"},
            {"npi": "1000000002", "taxonomy_code": "208D00000X"},
            {"npi": "1000000004", "taxonomy_code": "207R00000X"},
        ],
    )
    output_dir = tmp_path / "reports"

    report = report_changes.report_changes(
        old_provider_path,
        new_provider_path,
        old_taxonomy_path,
        new_taxonomy_path,
        output_dir,
    )
    saved_report = json.loads((output_dir / "nppes_snapshot_change_report.json").read_text())
    summary = (output_dir / "nppes_snapshot_change_summary.md").read_text(encoding="utf-8")

    assert report["newly_observed_npi_count"] == 1
    assert report["not_observed_in_newer_snapshot_count"] == 1
    assert report["deactivation_status_change_count"] == 1
    assert report["confirmed_newly_deactivated_count"] == 1
    assert report["primary_zip_change_count"] == 1
    assert report["taxonomy_set_change_count"] == 1
    assert saved_report["new_provider_count"] == 3
    assert "Newly observed NPIs" in summary
    assert "NPIs not observed in newer snapshot" in summary
    assert "new provider" not in summary.lower()
    assert "removed provider" not in summary.lower()
