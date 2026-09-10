"""Write aggregate-only lineage manifests for completed pipeline snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


SNAPSHOT_LABEL_PATTERN = "^[A-Za-z0-9_-]+$"
BRONZE_COUNT_KEYS = ("input_row_count", "massachusetts_row_count")
SILVER_COUNT_KEYS = (
    "input_row_count",
    "organization_records_excluded",
    "non_massachusetts_records_excluded",
    "primary_care_providers_retained",
    "missing_npi_count",
    "invalid_npi_count",
    "invalid_enumeration_date_count",
    "invalid_deactivation_date_count",
    "invalid_reactivation_date_count",
    "missing_zip_count",
    "missing_taxonomy_count",
)


class ManifestError(Exception):
    """An expected manifest-input problem, phrased for a command-line user."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write an aggregate-only lineage manifest for a completed NPPES snapshot."
    )
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--bronze-dir", required=True, type=Path)
    parser.add_argument("--silver-dir", required=True, type=Path)
    parser.add_argument("--gold-database", required=True, type=Path)
    parser.add_argument("--manifest-dir", required=True, type=Path)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    """Return a SHA-256 hash without loading the source ZIP into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit_sha(repository_root: Path) -> str | None:
    """Return the current commit SHA when Git is available, otherwise None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def read_json(path: Path, label: str) -> dict[str, object]:
    if not path.is_file():
        raise ManifestError(f"{label} JSON report was not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(
            f"Could not read {label} JSON report '{path.name}': {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ManifestError(f"{label} JSON report must contain an object: {path.name}")
    return payload


def count_values(
    payload: dict[str, object], keys: tuple[str, ...], label: str
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ManifestError(f"{label} JSON report has an invalid '{key}' count.")
        counts[key] = value
    return counts


def write_manifest(
    snapshot_label: str,
    source_zip: Path,
    bronze_dir: Path,
    silver_dir: Path,
    gold_database: Path,
    manifest_dir: Path,
    repository_root: Path | None = None,
) -> Path:
    """Write one aggregate-only manifest and return its path."""
    import re

    if not re.fullmatch(SNAPSHOT_LABEL_PATTERN, snapshot_label):
        raise ManifestError(
            "Snapshot label must contain only letters, numbers, underscores, and hyphens."
        )
    if not source_zip.is_file():
        raise ManifestError(f"Source ZIP was not found: {source_zip}")

    bronze_metadata_path = bronze_dir / f"{source_zip.stem}_massachusetts_metadata.json"
    silver_report_path = silver_dir / "transform_data_quality_report.json"
    bronze_metadata = read_json(bronze_metadata_path, "Bronze ingestion metadata")
    silver_report = read_json(silver_report_path, "Silver quality report")
    bronze_counts = count_values(
        bronze_metadata, BRONZE_COUNT_KEYS, "Bronze ingestion metadata"
    )
    silver_counts = count_values(
        silver_report, SILVER_COUNT_KEYS, "Silver quality report"
    )

    bronze_output_filename = bronze_metadata.get("output_filename")
    if not isinstance(bronze_output_filename, str) or not bronze_output_filename:
        raise ManifestError(
            "Bronze ingestion metadata has an invalid 'output_filename'."
        )

    root = repository_root or Path(__file__).resolve().parent.parent
    manifest = {
        "snapshot_label": snapshot_label,
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "source_zip_filename": source_zip.name,
        "source_zip_sha256": sha256_file(source_zip),
        "git_commit_sha": git_commit_sha(root),
        "output_paths": {
            "bronze_directory": str(bronze_dir),
            "bronze_parquet": str(bronze_dir / bronze_output_filename),
            "bronze_metadata": str(bronze_metadata_path),
            "silver_directory": str(silver_dir),
            "silver_providers": str(silver_dir / "providers_ma_primary_care.parquet"),
            "silver_provider_taxonomies": str(
                silver_dir / "provider_taxonomies.parquet"
            ),
            "silver_quality_report": str(silver_report_path),
            "gold_database": str(gold_database),
        },
        "bronze_counts": bronze_counts,
        "silver_data_quality_counts": silver_counts,
    }

    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{snapshot_label}.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        path = write_manifest(
            args.snapshot_label,
            args.source_zip,
            args.bronze_dir,
            args.silver_dir,
            args.gold_database,
            args.manifest_dir,
        )
    except ManifestError as error:
        print(f"Manifest creation stopped: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(
            f"Manifest creation stopped because a file could not be read or written: {error}",
            file=sys.stderr,
        )
        return 2
    print(f"Wrote aggregate-only run manifest: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
