# Data-layer contracts

## Physical layout

| Area | Physical location | Purpose |
| --- | --- | --- |
| Source landing | `data/raw/` | Local CMS NPPES ZIP files, unchanged and excluded from Git. |
| Bronze | `data/bronze/` | Massachusetts NPPES provider Parquet with minimal transformation and ingestion metadata. |
| Silver | `data/silver/` | Cleaned, conformed, taxonomy-normalized Version 1 primary-care Parquet tables and quality report. |
| Gold | `data/gold/` and `sql/gold/` | Local DuckDB database, Gold views, aggregate SQL, and aggregate change reports. |

## Source landing to Bronze

`src/ingest.py` confirms the expected main provider CSV, validates required raw fields and paired taxonomy fields, reads in chunks, retains configured fields, and filters the primary business-practice state to `MA`.

**Guarantees:** a Bronze run has documented source and retained-row counts, expected contract fields, retained available taxonomy slots, and only records whose primary practice state is Massachusetts.

**Known limitations:** Bronze is not raw because it is subsetted and converted to Parquet. It does not validate NPI format, normalize ZIP or dates, deduplicate NPIs, restrict entity type, or define the primary-care cohort. It includes only primary practice location information used by Version 1.

## Bronze to Silver

`src/transform.py` revalidates the required fields, retains individual providers, normalizes NPI, ZIP, and date fields, turns repeating taxonomy slots into a normalized table, and selects providers with any approved Version 1 primary-care taxonomy.

**Guarantees:** `providers_ma_primary_care.parquet` has at most one row per valid NPI; `provider_taxonomies.parquet` has at most one row per NPI-plus-taxonomy code; all retained providers have Massachusetts as the primary practice state and at least one approved taxonomy; and the transformation emits aggregate quality counts.

**Known limitations:** the taxonomy table retains all reported taxonomies for selected providers, not only the four approved codes. Missing or invalid NPI values prevent cohort retention, while incomplete address or phone values are flagged rather than deleted. Status is derived from the presence of a deactivation date; reactivation is retained but does not alter that Version 1 status rule. The cohort excludes organizations, advanced practice providers, subspecialties, and non-primary practice locations.

## Silver to Gold

`src/load.py` creates or replaces DuckDB tables from Silver Parquet and validates loaded row counts against source row counts. `sql/gold/models.sql` creates semantic views, and `sql/gold/analytics.sql` returns aggregate-only results. `src/report_changes.py` compares two Silver snapshots and writes aggregate reports to `data/gold/reports/`.

**Guarantees:** rerunning the loader replaces rather than appends DuckDB tables and views; Gold analytics and reports do not require returning provider-level rows.

**Known limitations:** source-versus-loaded row counts do not prove data completeness or business correctness. The DuckDB base tables are local copies of Silver data that support Gold views; the views and aggregate reports are the Gold analytical outputs. Weekly incremental files are not statewide baselines, so file presence differences must use cautious “newly observed” and “not observed” terminology.

## Cross-layer limitation

NPPES information is self-reported. It does not prove licensure, credentialing, network participation, appointment availability, whether a provider accepts new patients, or care access.
