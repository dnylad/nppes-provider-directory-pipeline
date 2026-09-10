"""Transform Bronze Massachusetts NPPES data into Silver Version 1 tables."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd


LOGGER = logging.getLogger(__name__)

NPI = "NPI"
ENTITY_TYPE = "Entity Type Code"
PRACTICE_STATE = "Provider Business Practice Location Address State Name"
PRACTICE_ZIP = "Provider Business Practice Location Address Postal Code"
ENUMERATION_DATE = "Provider Enumeration Date"
DEACTIVATION_DATE = "NPI Deactivation Date"
TAXONOMY_PREFIX = "Healthcare Provider Taxonomy Code_"
PRIMARY_TAXONOMY_PREFIX = "Healthcare Provider Primary Taxonomy Switch_"
INDIVIDUAL_ENTITY_TYPE = "1"
PRIMARY_CARE_CODES = {
    "207Q00000X",
    "207R00000X",
    "208D00000X",
    "208000000X",
}

# Exact NPPES fields documented in docs/data_contract.md that this step uses.
REQUIRED_BASE_COLUMNS = (
    NPI,
    ENTITY_TYPE,
    "Provider Last Name (Legal Name)",
    "Provider First Name",
    "Provider Middle Name",
    "Provider Name Prefix Text",
    "Provider Name Suffix Text",
    "Provider Credential Text",
    "Provider First Line Business Practice Location Address",
    "Provider Second Line Business Practice Location Address",
    "Provider Business Practice Location Address City Name",
    "Provider Business Practice Location Address State Name",
    PRACTICE_ZIP,
    "Provider Business Practice Location Address Country Code (If outside U.S.)",
    "Provider Business Practice Location Address Telephone Number",
    "Provider Business Practice Location Address Fax Number",
    ENUMERATION_DATE,
    "NPI Deactivation Reason Code",
    DEACTIVATION_DATE,
    "NPI Reactivation Date",
)


class TransformError(Exception):
    """An expected input or output problem, written for a command-line user."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create Silver Version 1 Massachusetts primary-care provider and taxonomy "
            "Parquet tables from a Bronze ingestion Parquet file."
        )
    )
    parser.add_argument(
        "input_parquet",
        type=Path,
        help="Bronze Massachusetts Parquet file created by src/ingest.py.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Silver output directory for conformed Parquet files and the quality report.",
    )
    return parser.parse_args(argv)


def clean_text(series: pd.Series) -> pd.Series:
    """Return trimmed strings with blank values represented as missing."""
    cleaned = series.fillna("").astype(str).str.strip()
    return cleaned.mask(cleaned.eq(""))


def normalize_npi(series: pd.Series) -> tuple[pd.Series, int, int]:
    """Normalize valid NPIs and return missing/invalid counts from raw values."""
    raw = clean_text(series)
    missing_count = int(raw.isna().sum())
    valid = raw.str.fullmatch(r"\d{10}").eq(True)
    invalid_count = int((raw.notna() & ~valid).sum())
    return raw.where(valid), missing_count, invalid_count


def normalize_zip(series: pd.Series) -> tuple[pd.Series, int]:
    """Keep the first five digits of usable ZIP or ZIP+4 values."""
    raw = clean_text(series)
    normalized = raw.str.extract(r"^(\d{5})(?:-?\d{4})?$", expand=False)
    missing_count = int(normalized.isna().sum())
    return normalized, missing_count


def normalize_date(series: pd.Series) -> tuple[pd.Series, int]:
    """Parse a date field and render valid values in ISO YYYY-MM-DD form."""
    raw = clean_text(series)
    parsed = pd.to_datetime(raw, errors="coerce")
    invalid_count = int((raw.notna() & parsed.isna()).sum())
    return parsed.dt.strftime("%Y-%m-%d"), invalid_count


def taxonomy_field_pairs(columns: Sequence[str]) -> list[tuple[int, str, str]]:
    """Discover exact numbered taxonomy and primary-switch fields."""
    available = set(columns)
    code_fields: list[tuple[int, str, str]] = []
    for column in columns:
        match = re.fullmatch(r"Healthcare Provider Taxonomy Code_(\d+)", column)
        if match:
            slot = int(match.group(1))
            primary_field = f"{PRIMARY_TAXONOMY_PREFIX}{slot}"
            if primary_field not in available:
                raise TransformError(
                    f"The taxonomy field '{column}' is missing its corresponding "
                    f"primary-taxonomy field '{primary_field}'."
                )
            code_fields.append((slot, column, primary_field))
    if not code_fields:
        raise TransformError(
            "No 'Healthcare Provider Taxonomy Code_n' fields were found in the input Parquet."
        )
    return sorted(code_fields)


def validate_columns(frame: pd.DataFrame) -> list[tuple[int, str, str]]:
    missing = [column for column in REQUIRED_BASE_COLUMNS if column not in frame.columns]
    if missing:
        raise TransformError(
            "Input Parquet is missing required fields from docs/data_contract.md: "
            + ", ".join(missing)
        )
    return taxonomy_field_pairs(frame.columns.tolist())


def build_taxonomies(
    individual_records: pd.DataFrame,
    field_pairs: Sequence[tuple[int, str, str]],
) -> pd.DataFrame:
    """Normalize all populated taxonomy slots into one row per NPI/taxonomy."""
    tables: list[pd.DataFrame] = []
    for slot, taxonomy_field, primary_field in field_pairs:
        values = pd.DataFrame(
            {
                "npi": individual_records["npi"],
                "taxonomy_code": clean_text(individual_records[taxonomy_field]).str.upper(),
                "primary_taxonomy_flag": clean_text(individual_records[primary_field]).str.upper(),
                "taxonomy_slot": slot,
            }
        )
        tables.append(values.loc[values["taxonomy_code"].notna()])

    if not tables:
        return pd.DataFrame(
            columns=["npi", "taxonomy_code", "primary_taxonomy_flag", "taxonomy_slot"]
        )
    # NPPES can repeat the same code in more than one numbered slot. The
    # normalized table's grain is one NPI-plus-taxonomy-code pair, so retain
    # the first source slot and avoid duplicate analytical counts.
    return pd.concat(tables, ignore_index=True).drop_duplicates(
        subset=["npi", "taxonomy_code"], keep="first"
    )


def provider_table(cohort: pd.DataFrame) -> pd.DataFrame:
    """Return exactly one normalized provider row per valid NPI."""
    providers = pd.DataFrame(
        {
            "npi": cohort["npi"],
            "entity_type_code": clean_text(cohort[ENTITY_TYPE]),
            "provider_last_name": clean_text(cohort["Provider Last Name (Legal Name)"]),
            "provider_first_name": clean_text(cohort["Provider First Name"]),
            "provider_middle_name": clean_text(cohort["Provider Middle Name"]),
            "provider_name_prefix": clean_text(cohort["Provider Name Prefix Text"]),
            "provider_name_suffix": clean_text(cohort["Provider Name Suffix Text"]),
            "provider_credential": clean_text(cohort["Provider Credential Text"]),
            "practice_address_line_1": clean_text(
                cohort["Provider First Line Business Practice Location Address"]
            ),
            "practice_address_line_2": clean_text(
                cohort["Provider Second Line Business Practice Location Address"]
            ),
            "practice_city": clean_text(
                cohort["Provider Business Practice Location Address City Name"]
            ),
            "practice_state": clean_text(
                cohort["Provider Business Practice Location Address State Name"]
            ).str.upper(),
            "practice_zip": cohort["normalized_zip"],
            "practice_country_code": clean_text(
                cohort["Provider Business Practice Location Address Country Code (If outside U.S.)"]
            ),
            "practice_phone": clean_text(
                cohort["Provider Business Practice Location Address Telephone Number"]
            ),
            "practice_fax": clean_text(
                cohort["Provider Business Practice Location Address Fax Number"]
            ),
            "enumeration_date": cohort["normalized_enumeration_date"],
            "deactivation_reason_code": clean_text(cohort["NPI Deactivation Reason Code"]),
            "deactivation_date": cohort["normalized_deactivation_date"],
            "reactivation_date": cohort["normalized_reactivation_date"],
        }
    )
    providers["status"] = providers["deactivation_date"].notna().map(
        {True: "deactivated", False: "active"}
    )
    return providers.drop_duplicates(subset="npi", keep="first").reset_index(drop=True)


def transform(input_parquet: Path, output_dir: Path) -> dict[str, object]:
    """Create Silver Version 1 Parquet tables and an aggregate quality report."""
    if not input_parquet.is_file():
        raise TransformError(
            f"Input Parquet not found: {input_parquet}. Run src/ingest.py first or check the path."
        )
    if input_parquet.suffix.lower() != ".parquet":
        raise TransformError(f"Input must be a .parquet file, not: {input_parquet.name}")

    try:
        frame = pd.read_parquet(input_parquet)
    except (OSError, ValueError, ImportError) as error:
        raise TransformError(
            f"Could not read '{input_parquet.name}' as Parquet: {error}"
        ) from error

    field_pairs = validate_columns(frame)
    input_row_count = len(frame)
    frame["npi"], missing_npi_count, invalid_npi_count = normalize_npi(frame[NPI])
    frame["normalized_zip"], missing_zip_count = normalize_zip(frame[PRACTICE_ZIP])
    frame["normalized_enumeration_date"], invalid_enumeration_date_count = normalize_date(
        frame[ENUMERATION_DATE]
    )
    frame["normalized_deactivation_date"], invalid_deactivation_date_count = normalize_date(
        frame[DEACTIVATION_DATE]
    )
    frame["normalized_reactivation_date"], invalid_reactivation_date_count = normalize_date(
        frame["NPI Reactivation Date"]
    )

    practice_state = clean_text(frame[PRACTICE_STATE]).str.upper()
    non_massachusetts_records_excluded = int(practice_state.ne("MA").sum())
    massachusetts_records = frame.loc[practice_state.eq("MA")].copy()

    entity_type = clean_text(frame[ENTITY_TYPE])
    organization_records_excluded = int(entity_type.eq("2").sum())
    individual_records = massachusetts_records.loc[
        clean_text(massachusetts_records[ENTITY_TYPE]).eq(INDIVIDUAL_ENTITY_TYPE)
    ].copy()
    valid_individual_records = individual_records.loc[individual_records["npi"].notna()].copy()

    taxonomies = build_taxonomies(valid_individual_records, field_pairs)
    npis_with_taxonomy = set(taxonomies["npi"])
    missing_taxonomy_count = int(
        valid_individual_records["npi"].map(lambda npi: npi not in npis_with_taxonomy).sum()
    )
    cohort_npis = set(
        taxonomies.loc[taxonomies["taxonomy_code"].isin(PRIMARY_CARE_CODES), "npi"]
    )
    cohort_records = valid_individual_records.loc[
        valid_individual_records["npi"].isin(cohort_npis)
    ].copy()
    providers = provider_table(cohort_records)
    cohort_taxonomies = taxonomies.loc[taxonomies["npi"].isin(set(providers["npi"]))].copy()
    cohort_taxonomies = cohort_taxonomies.sort_values(
        ["npi", "taxonomy_slot", "taxonomy_code"], ignore_index=True
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    providers_path = output_dir / "providers_ma_primary_care.parquet"
    taxonomies_path = output_dir / "provider_taxonomies.parquet"
    quality_report_path = output_dir / "transform_data_quality_report.json"
    providers.to_parquet(providers_path, index=False)
    cohort_taxonomies.to_parquet(taxonomies_path, index=False)

    report: dict[str, object] = {
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "input_row_count": int(input_row_count),
        "organization_records_excluded": organization_records_excluded,
        "non_massachusetts_records_excluded": non_massachusetts_records_excluded,
        "primary_care_providers_retained": int(len(providers)),
        "missing_npi_count": missing_npi_count,
        "invalid_npi_count": invalid_npi_count,
        "invalid_enumeration_date_count": invalid_enumeration_date_count,
        "invalid_deactivation_date_count": invalid_deactivation_date_count,
        "invalid_reactivation_date_count": invalid_reactivation_date_count,
        "missing_zip_count": missing_zip_count,
        "missing_taxonomy_count": missing_taxonomy_count,
        "providers_output_filename": providers_path.name,
        "provider_taxonomies_output_filename": taxonomies_path.name,
    }
    quality_report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    LOGGER.info(
        "Finished transformation: %s input rows, %s organization records excluded, "
        "%s primary-care providers retained.",
        input_row_count,
        organization_records_excluded,
        len(providers),
    )
    LOGGER.info("Wrote Silver outputs to %s.", output_dir)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        transform(args.input_parquet, args.output_dir)
    except TransformError as error:
        LOGGER.error("Transformation stopped: %s", error)
        return 2
    except (OSError, PermissionError) as error:
        LOGGER.error("Transformation stopped because a file could not be read or written: %s", error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
