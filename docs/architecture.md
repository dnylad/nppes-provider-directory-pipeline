# Architecture overview

The project will follow a simple local data-engineering flow:

1. Place source provider-directory files in `data/raw/`.
2. Use Python code in `src/` and SQL in `sql/` to clean and transform data.
3. Store analysis-ready Parquet files in `data/processed/`.
4. Use DuckDB to query Parquet data locally.
5. Use pytest for automated checks, including tests against small files in `data/sample/`.
6. Run the test suite on every GitHub push and pull request through GitHub Actions.

No ingestion, transformation, or data model has been implemented yet.
