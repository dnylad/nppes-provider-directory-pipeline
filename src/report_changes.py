"""Compare aggregate changes between two Silver NPPES primary-care snapshots."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


LOGGER = logging.getLogger(__name__)

PROVIDER_REQUIRED_COLUMNS = ("npi", "status", "deactivation_date", "practice_zip")
TAXONOMY_REQUIRED_COLUMNS = ("npi", "taxonomy_code")
DEFAULT_OUTPUT_DIR = Path("data/gold/reports")


class ChangeReportError(Exception):
    """An expected comparison problem, written for a command-line user."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two Silver NPPES primary-care snapshots and write Gold aggregate-only reports."
        )
    )
    parser.add_argument(
        "old_providers", type=Path, help="Older providers Parquet file."
    )
    parser.add_argument(
        "new_providers", type=Path, help="Newer providers Parquet file."
    )
    parser.add_argument(
        "old_taxonomies", type=Path, help="Older provider-taxonomies Parquet file."
    )
    parser.add_argument(
        "new_taxonomies", type=Path, help="Newer provider-taxonomies Parquet file."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Gold directory for Markdown and JSON reports (default: data/gold/reports).",
    )
    return parser.parse_args(argv)


def clean_text(series: pd.Series) -> pd.Series:
    """Return trimmed strings with blank values represented as missing."""
    values = series.fillna("").astype(str).str.strip()
    return values.mask(values.eq(""))


def read_parquet(
    path: Path, required_columns: Iterable[str], label: str
) -> pd.DataFrame:
    if not path.is_file():
        raise ChangeReportError(f"{label} file not found: {path}")
    if path.suffix.lower() != ".parquet":
        raise ChangeReportError(f"{label} input must be a .parquet file: {path.name}")
    try:
        frame = pd.read_parquet(path)
    except (OSError, ValueError, ImportError) as error:
        raise ChangeReportError(
            f"Could not read {label} Parquet '{path.name}': {error}"
        ) from error

    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ChangeReportError(
            f"{label} Parquet '{path.name}' is missing required column(s): {', '.join(missing)}"
        )
    return frame


def prepare_providers(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Normalize provider comparison fields and reject ambiguous snapshot keys."""
    prepared = frame.loc[:, list(PROVIDER_REQUIRED_COLUMNS)].copy()
    prepared["npi"] = clean_text(prepared["npi"])
    if prepared["npi"].isna().any():
        raise ChangeReportError(
            f"{label} providers contains a missing NPI and cannot be compared safely."
        )
    if prepared["npi"].duplicated().any():
        raise ChangeReportError(
            f"{label} providers contains duplicate NPIs and cannot be compared safely."
        )
    prepared["status"] = clean_text(prepared["status"]).str.lower()
    prepared["deactivation_date"] = clean_text(prepared["deactivation_date"])
    prepared["practice_zip"] = clean_text(prepared["practice_zip"])
    return prepared.set_index("npi", drop=False)


def taxonomy_sets(
    frame: pd.DataFrame, known_npis: set[str]
) -> dict[str, frozenset[str]]:
    """Return distinct, normalized taxonomy-code sets for provider NPIs."""
    taxonomies = frame.loc[:, list(TAXONOMY_REQUIRED_COLUMNS)].copy()
    taxonomies["npi"] = clean_text(taxonomies["npi"])
    taxonomies["taxonomy_code"] = clean_text(taxonomies["taxonomy_code"]).str.upper()
    taxonomies = taxonomies.loc[
        taxonomies["npi"].notna()
        & taxonomies["taxonomy_code"].notna()
        & taxonomies["npi"].isin(known_npis)
    ]
    grouped = taxonomies.groupby("npi")["taxonomy_code"].agg(
        lambda codes: frozenset(codes)
    )
    return {npi: codes for npi, codes in grouped.items()}


def compare_snapshots(
    old_providers: pd.DataFrame,
    new_providers: pd.DataFrame,
    old_taxonomies: pd.DataFrame,
    new_taxonomies: pd.DataFrame,
) -> dict[str, int]:
    """Calculate cautious aggregate snapshot differences without returning NPIs."""
    old = prepare_providers(old_providers, "Older snapshot")
    new = prepare_providers(new_providers, "Newer snapshot")
    old_npis = set(old.index)
    new_npis = set(new.index)
    shared_npis = old_npis & new_npis

    old_taxonomy_sets = taxonomy_sets(old_taxonomies, old_npis)
    new_taxonomy_sets = taxonomy_sets(new_taxonomies, new_npis)

    status_changed = sum(
        old.at[npi, "status"] != new.at[npi, "status"] for npi in shared_npis
    )
    confirmed_newly_deactivated = sum(
        old.at[npi, "status"] != "deactivated"
        and new.at[npi, "status"] == "deactivated"
        and pd.notna(new.at[npi, "deactivation_date"])
        for npi in shared_npis
    )
    zip_changed = sum(
        old.at[npi, "practice_zip"] != new.at[npi, "practice_zip"]
        for npi in shared_npis
    )
    taxonomy_changed = sum(
        old_taxonomy_sets.get(npi, frozenset())
        != new_taxonomy_sets.get(npi, frozenset())
        for npi in shared_npis
    )

    return {
        "old_provider_count": len(old_npis),
        "new_provider_count": len(new_npis),
        "newly_observed_npi_count": len(new_npis - old_npis),
        "not_observed_in_newer_snapshot_count": len(old_npis - new_npis),
        "deactivation_status_change_count": status_changed,
        "confirmed_newly_deactivated_count": confirmed_newly_deactivated,
        "primary_zip_change_count": zip_changed,
        "taxonomy_set_change_count": taxonomy_changed,
    }


def markdown_summary(report: dict[str, object]) -> str:
    """Render a cautious aggregate-only Markdown summary."""
    return f"""# NPPES primary-care snapshot change summary

## Important interpretation note

This comparison is based on file presence and Silver snapshot attributes.
“Newly observed” and “not observed in the newer snapshot” describe differences
between files; they do not prove a provider entered or left the market. A
deactivation is identified only when the newer status is `deactivated` and a
newer deactivation date is present.

## Aggregate comparison

| Measure | Count |
| --- | ---: |
| Providers in older snapshot | {report["old_provider_count"]} |
| Providers in newer snapshot | {report["new_provider_count"]} |
| Newly observed NPIs | {report["newly_observed_npi_count"]} |
| NPIs not observed in newer snapshot | {report["not_observed_in_newer_snapshot_count"]} |
| Deactivation-status changes | {report["deactivation_status_change_count"]} |
| Confirmed newly deactivated NPIs | {report["confirmed_newly_deactivated_count"]} |
| Primary ZIP-code changes | {report["primary_zip_change_count"]} |
| Taxonomy-set changes | {report["taxonomy_set_change_count"]} |

## Incremental-file limitation

When either snapshot is a weekly incremental file, it is not a complete
statewide baseline. Absence from a newer incremental file must not be treated
as a removal. Compare future weekly files with a monthly full replacement
baseline for more reliable change interpretation.
"""


def report_changes(
    old_providers_path: Path,
    new_providers_path: Path,
    old_taxonomies_path: Path,
    new_taxonomies_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    """Compare snapshots and write aggregate Markdown and JSON reports."""
    old_providers = read_parquet(
        old_providers_path, PROVIDER_REQUIRED_COLUMNS, "Older providers"
    )
    new_providers = read_parquet(
        new_providers_path, PROVIDER_REQUIRED_COLUMNS, "Newer providers"
    )
    old_taxonomies = read_parquet(
        old_taxonomies_path, TAXONOMY_REQUIRED_COLUMNS, "Older taxonomy"
    )
    new_taxonomies = read_parquet(
        new_taxonomies_path, TAXONOMY_REQUIRED_COLUMNS, "Newer taxonomy"
    )

    metrics = compare_snapshots(
        old_providers, new_providers, old_taxonomies, new_taxonomies
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "nppes_snapshot_change_summary.md"
    json_path = output_dir / "nppes_snapshot_change_report.json"
    report: dict[str, object] = {
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "old_providers_filename": old_providers_path.name,
        "new_providers_filename": new_providers_path.name,
        "old_taxonomies_filename": old_taxonomies_path.name,
        "new_taxonomies_filename": new_taxonomies_path.name,
        **metrics,
        "markdown_summary_filename": markdown_path.name,
    }
    markdown_path.write_text(markdown_summary(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "Compared snapshots: %s newly observed, %s not observed in newer snapshot, "
        "%s taxonomy-set changes.",
        metrics["newly_observed_npi_count"],
        metrics["not_observed_in_newer_snapshot_count"],
        metrics["taxonomy_set_change_count"],
    )
    LOGGER.info("Wrote aggregate change reports to %s.", output_dir)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        report_changes(
            args.old_providers,
            args.new_providers,
            args.old_taxonomies,
            args.new_taxonomies,
            args.output_dir,
        )
    except ChangeReportError as error:
        LOGGER.error("Change report stopped: %s", error)
        return 2
    except OSError as error:
        LOGGER.error(
            "Change report stopped because a file could not be read or written: %s",
            error,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
