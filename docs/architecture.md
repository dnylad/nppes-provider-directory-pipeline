# Architecture overview

## Scope

**Project:** NPPES Provider Directory Change Pipeline

**Geography:** Massachusetts

**Provider cohort:** primary care

### Problem statement

Healthcare operations, provider-directory, and network teams need an auditable way to measure the Massachusetts primary-care directory footprint and identify meaningful changes across NPPES releases. The pipeline will replace manual source-file comparisons with reproducible outputs.

### Intended users

- Healthcare operations teams
- Provider-directory teams
- Provider network teams

### Intended questions

The eventual pipeline will support analysis of:

- Provider counts by Massachusetts ZIP code
- Completeness of key directory fields
- New records and deactivations between releases
- Practice-address changes
- Taxonomy changes

### Preliminary primary-care definition (assumption)

For the initial scope, a provider is considered primary care when its NPPES record contains a Family Medicine, Internal Medicine, General Practice, or Pediatrics taxonomy. This is a working assumption that can be expanded later with stakeholder input.

### Data limitation

NPPES information is self-reported. An NPI does not prove licensure, credentialing, network participation, or whether a provider accepts new patients.

## Planned architecture

The project will follow a simple local data-engineering flow:

1. Place source provider-directory files in `data/raw/`.
2. Use Python code in `src/` and SQL in `sql/` to clean and transform data.
3. Store analysis-ready Parquet files in `data/processed/`.
4. Use DuckDB to query Parquet data locally.
5. Use pytest for automated checks, including tests against small files in `data/sample/`.
6. Run the test suite on every GitHub push and pull request through GitHub Actions.

No ingestion, transformation, or data model has been implemented yet.
