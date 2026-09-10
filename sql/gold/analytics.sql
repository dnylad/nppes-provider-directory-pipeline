-- Gold aggregate analytics for the Massachusetts primary-care provider cohort.
-- These queries intentionally return summary metrics only, never provider rows.

-- 1. Healthcare operations question: How many active primary-care providers
-- are currently represented in the Massachusetts cohort?
SELECT
    COUNT(*) AS active_primary_care_provider_count
FROM active_primary_care_providers;

-- 2. Healthcare operations question: Which approved primary-care specialties
-- have the largest active provider footprint? A provider may appear in more
-- than one specialty count when it reports multiple approved taxonomies.
SELECT
    taxonomy_code,
    provider_count
FROM provider_counts_by_taxonomy
WHERE taxonomy_code IN (
    '207Q00000X',
    '207R00000X',
    '208D00000X',
    '208000000X'
)
ORDER BY taxonomy_code;

-- 3. Healthcare operations question: How is the active provider footprint
-- distributed across primary-practice ZIP codes?
SELECT
    practice_zip,
    provider_count
FROM provider_counts_by_zip
ORDER BY practice_zip;

-- 4. Healthcare operations question: Which ten ZIP codes have the largest
-- active primary-care provider counts for local network planning?
SELECT
    practice_zip,
    provider_count
FROM provider_counts_by_zip
ORDER BY provider_count DESC, practice_zip
LIMIT 10;

-- 5. Healthcare operations question: What is the current active versus
-- deactivated mix in the Massachusetts primary-care provider table?
SELECT
    status,
    COUNT(*) AS provider_count
FROM providers
GROUP BY status
ORDER BY status;

-- 6. Healthcare operations question: Are key directory fields complete for
-- the cohort, including ZIP, phone, and taxonomy information?
SELECT
    missing_zip_count,
    missing_phone_count,
    missing_taxonomy_count
FROM data_completeness_summary;

-- 7. Healthcare operations question: How many providers have multiple
-- taxonomy assignments, indicating multi-specialty directory representation?
SELECT
    COUNT(*) AS providers_with_multiple_taxonomy_assignments
FROM (
    SELECT
        npi
    FROM provider_taxonomies
    GROUP BY npi
    HAVING COUNT(*) > 1
) AS multi_taxonomy_providers;
