# nppes-provider-directory-pipeline

## Project purpose

This beginner-friendly Python data-engineering project will eventually turn NPPES provider-directory source data into clean, queryable Parquet datasets. It is intentionally set up as a project skeleton only: no data pipeline has been implemented yet.

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
