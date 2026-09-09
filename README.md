# nppes-provider-directory-pipeline

## Project purpose

This beginner-friendly Python data-engineering project will eventually turn NPPES provider-directory source data into clean, queryable Parquet datasets. It is intentionally set up as a project skeleton only: no data pipeline has been implemented yet.

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
