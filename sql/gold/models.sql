-- Gold semantic views for the local NPPES DuckDB warehouse.

CREATE OR REPLACE VIEW active_primary_care_providers AS
SELECT *
FROM providers
WHERE status = 'active';

CREATE OR REPLACE VIEW provider_counts_by_zip AS
SELECT
    practice_zip,
    COUNT(*) AS provider_count
FROM active_primary_care_providers
GROUP BY practice_zip;

CREATE OR REPLACE VIEW provider_counts_by_taxonomy AS
SELECT
    provider_taxonomies.taxonomy_code,
    COUNT(DISTINCT active_primary_care_providers.npi) AS provider_count
FROM active_primary_care_providers
INNER JOIN provider_taxonomies
    ON active_primary_care_providers.npi = provider_taxonomies.npi
GROUP BY provider_taxonomies.taxonomy_code;

CREATE OR REPLACE VIEW data_completeness_summary AS
SELECT
    COUNT(*) AS provider_count,
    COUNT(*) FILTER (
        WHERE practice_zip IS NULL OR TRIM(practice_zip) = ''
    ) AS missing_zip_count,
    COUNT(*) FILTER (
        WHERE practice_address_line_1 IS NULL OR TRIM(practice_address_line_1) = ''
    ) AS missing_address_line_1_count,
    COUNT(*) FILTER (
        WHERE practice_phone IS NULL OR TRIM(practice_phone) = ''
    ) AS missing_phone_count,
    COUNT(*) FILTER (
        WHERE enumeration_date IS NULL OR TRIM(enumeration_date) = ''
    ) AS missing_enumeration_date_count,
    COUNT(*) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM provider_taxonomies
            WHERE provider_taxonomies.npi = providers.npi
        )
    ) AS missing_taxonomy_count
FROM providers;
