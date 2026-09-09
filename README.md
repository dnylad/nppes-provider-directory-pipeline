# nppes-provider-directory-pipeline

[![Tests](https://github.com/dnylad/nppes-provider-directory-pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/dnylad/nppes-provider-directory-pipeline/actions/workflows/tests.yml)

## Project purpose

This beginner-friendly Python data-engineering project turns NPPES provider-directory source data into clean, queryable Parquet datasets. The first ingestion step streams weekly source data from its ZIP archive and produces a Massachusetts subset; primary-care and change-analysis transformations will follow in later steps.

## Project scope

**NPPES Provider Directory Change Pipeline** focuses on primary-care providers in Massachusetts. It will help healthcare operations, provider-directory, and network teams understand the size, quality, and changes in this provider cohort over time.

### Problem statement

Provider-directory teams need a repeatable way to understand where primary-care providers are listed, how complete their NPPES records are, and what changes between published NPPES data releases. Manually comparing large source files is slow and difficult to audit.

### Questions the pipeline will answer

- How many in-scope providers are listed by Massachusetts ZIP code?
- How complete are key directory fields, such as practice address and taxonomy?
- Which provider records are new, deactivated, or no longer present between releases?
- Which records have practice-address or taxonomy changes?

### Preliminary primary-care definition (assumption)

Until the cohort definition is refined with stakeholders, primary care means providers with at least one of these NPPES taxonomy families:

- Family Medicine
- Internal Medicine
- General Practice
- Pediatrics

This is an assumption, not a final clinical or network definition, and can be expanded later.

### Important limitation

NPPES information is self-reported. An NPI record does **not** prove licensure, credentialing, network participation, or whether a provider accepts new patients.

## Project layout

- `data/raw/` — original input files, kept unchanged.
- `data/sample/` — small, safe example files for local development and tests.
- `data/interim/` — generated ingestion-stage Parquet files and run metadata (not committed to Git).
- `data/processed/` — generated Parquet outputs (not committed to Git).
- `src/` — future Python pipeline code.
- `sql/` — future DuckDB SQL queries and transformations.
- `tests/` — pytest test modules.
- `docs/` — project documentation, including the architecture overview.

## Planned tools

Python, pandas, DuckDB, Parquet, pytest, and GitHub Actions.

## Getting started

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the ingestion step

The ingestion command streams the main NPPES provider CSV from a ZIP archive,
filters it to primary business-practice locations in Massachusetts, and writes
a Parquet file plus JSON run metadata. The source ZIP is read in place and is
not extracted to disk.

```powershell
.\.venv\Scripts\python.exe src\ingest.py `
  data\raw\NPPES_Data_Dissemination_080326_080926_Weekly_V2.zip `
  data\interim
```

Use `--help` to see the optional chunk-size setting. Generated interim files
and raw NPPES data are excluded from Git.

## Run the transformation step

The transformation command keeps individual Massachusetts providers, selects
the Version 1 primary-care cohort, and writes provider, taxonomy, and
data-quality outputs. It does not print provider-level records.

```powershell
.\.venv\Scripts\python.exe src\transform.py `
  data\interim\NPPES_Data_Dissemination_080326_080926_Weekly_V2_massachusetts.parquet `
  data\processed
```

Generated processed files are excluded from Git.

## Run the load step

The load command creates a local DuckDB analytics database from the processed
Parquet files. Rerunning it replaces the tables and views, so it does not add
duplicate rows.

```powershell
.\.venv\Scripts\python.exe src\load.py `
  data\processed `
  data\warehouse\nppes_provider_directory.duckdb
```

The DuckDB database and other warehouse files are excluded from Git.
