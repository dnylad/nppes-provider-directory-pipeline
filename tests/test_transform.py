"""Synthetic unit tests for the Version 1 NPPES transformation rules."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src import transform


APPROVED_CODE = "207Q00000X"


def synthetic_record(**overrides: str) -> dict[str, str]:
    """Build one non-real record with all contract fields used by transform.py."""
    record = {
        "NPI": "1000000001",
        "Entity Type Code": "1",
        "Provider Last Name (Legal Name)": "Synthetic",
        "Provider First Name": "Example",
        "Provider Middle Name": "",
        "Provider Name Prefix Text": "",
        "Provider Name Suffix Text": "",
        "Provider Credential Text": "",
        "Provider First Line Business Practice Location Address": "1 Test Way",
        "Provider Second Line Business Practice Location Address": "",
        "Provider Business Practice Location Address City Name": "Testville",
        "Provider Business Practice Location Address State Name": "MA",
        "Provider Business Practice Location Address Postal Code": "02108-1234",
        "Provider Business Practice Location Address Country Code (If outside U.S.)": "US",
        "Provider Business Practice Location Address Telephone Number": "5555550100",
        "Provider Business Practice Location Address Fax Number": "",
        "Provider Enumeration Date": "2020-01-15",
        "NPI Deactivation Reason Code": "",
        "NPI Deactivation Date": "",
        "NPI Reactivation Date": "",
        "Healthcare Provider Taxonomy Code_1": APPROVED_CODE,
        "Healthcare Provider Primary Taxonomy Switch_1": "Y",
        "Healthcare Provider Taxonomy Code_2": "",
        "Healthcare Provider Primary Taxonomy Switch_2": "",
    }
    record.update(overrides)
    return record


def run_transform(tmp_path: Path, records: list[dict[str, str]]):
    """Run the real transformation against a tiny synthetic Parquet input."""
    input_path = tmp_path / "synthetic_input.parquet"
    output_dir = tmp_path / "silver"
    pd.DataFrame(records).to_parquet(input_path, index=False)
    report = transform.transform(input_path, output_dir)
    providers = pd.read_parquet(output_dir / "providers_ma_primary_care.parquet")
    taxonomies = pd.read_parquet(output_dir / "provider_taxonomies.parquet")
    saved_report = json.loads(
        (output_dir / "transform_data_quality_report.json").read_text(encoding="utf-8")
    )
    return providers, taxonomies, report, saved_report


def test_valid_massachusetts_individual_with_approved_taxonomy_is_retained(tmp_path: Path):
    providers, taxonomies, report, _ = run_transform(tmp_path, [synthetic_record()])

    assert len(providers) == 1
    assert len(taxonomies) == 1
    assert report["primary_care_providers_retained"] == 1


def test_non_primary_approved_taxonomy_retains_provider(tmp_path: Path):
    record = synthetic_record(
        **{
            "Healthcare Provider Taxonomy Code_1": "122300000X",
            "Healthcare Provider Primary Taxonomy Switch_1": "Y",
            "Healthcare Provider Taxonomy Code_2": "207R00000X",
            "Healthcare Provider Primary Taxonomy Switch_2": "N",
        }
    )
    providers, taxonomies, _, _ = run_transform(tmp_path, [record])

    assert len(providers) == 1
    assert "207R00000X" in set(taxonomies["taxonomy_code"])
    assert taxonomies.loc[
        taxonomies["taxonomy_code"].eq("207R00000X"), "primary_taxonomy_flag"
    ].item() == "N"


def test_organization_record_is_excluded(tmp_path: Path):
    providers, taxonomies, report, _ = run_transform(
        tmp_path,
        [synthetic_record(**{"Entity Type Code": "2"})],
    )

    assert providers.empty
    assert taxonomies.empty
    assert report["organization_records_excluded"] == 1


def test_missing_and_invalid_npis_are_flagged(tmp_path: Path):
    records = [synthetic_record(**{"NPI": ""}), synthetic_record(**{"NPI": "not-an-npi"})]
    providers, _, report, saved_report = run_transform(tmp_path, records)

    assert providers.empty
    assert report["missing_npi_count"] == 1
    assert report["invalid_npi_count"] == 1
    assert saved_report["missing_npi_count"] == 1
    assert saved_report["invalid_npi_count"] == 1


def test_non_massachusetts_record_is_excluded(tmp_path: Path):
    providers, taxonomies, report, _ = run_transform(
        tmp_path,
        [
            synthetic_record(
                **{"Provider Business Practice Location Address State Name": "NY"}
            )
        ],
    )

    assert providers.empty
    assert taxonomies.empty
    assert report["non_massachusetts_records_excluded"] == 1


def test_deactivation_date_sets_deactivated_status(tmp_path: Path):
    providers, _, _, _ = run_transform(
        tmp_path,
        [synthetic_record(**{"NPI Deactivation Date": "2024-02-03"})],
    )

    assert providers.loc[0, "deactivation_date"] == "2024-02-03"
    assert providers.loc[0, "status"] == "deactivated"


def test_duplicate_npi_plus_taxonomy_pairs_are_not_produced(tmp_path: Path):
    record = synthetic_record(
        **{
            "Healthcare Provider Taxonomy Code_2": APPROVED_CODE,
            "Healthcare Provider Primary Taxonomy Switch_2": "N",
        }
    )
    _, taxonomies, _, _ = run_transform(tmp_path, [record])

    assert len(taxonomies) == 1
    assert not taxonomies.duplicated(["npi", "taxonomy_code"]).any()
