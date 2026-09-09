# Initial findings

## Executive summary

The weekly NPPES incremental file produced an initial Massachusetts
primary-care directory cohort of 48 providers: 47 active and 1 deactivated.
The active cohort spans 24 primary-practice ZIP codes. Internal Medicine is
the largest approved taxonomy group in this incremental sample.

These findings describe directory records in this file, not the availability
or accessibility of care.

## Provider status

| Status | Provider count |
| --- | ---: |
| Active | 47 |
| Deactivated | 1 |

## Approved primary-care taxonomy mix

A provider can contribute to more than one taxonomy count when it reports
multiple approved taxonomies.

| Taxonomy | Code | Active provider count |
| --- | --- | ---: |
| Family Medicine | `207Q00000X` | 6 |
| Internal Medicine | `207R00000X` | 31 |
| General Practice | `208D00000X` | 3 |
| Pediatrics | `208000000X` | 11 |

## Directory coverage by ZIP code

The active cohort is represented in **24 Massachusetts ZIP codes**. The ten
ZIP codes with the highest active directory counts are:

| ZIP code | Active provider count |
| --- | ---: |
| `02115` | 9 |
| `02114` | 7 |
| `01805` | 3 |
| `02215` | 3 |
| `01605` | 2 |
| `01742` | 2 |
| `01970` | 2 |
| `02111` | 2 |
| `02118` | 2 |
| `01103` | 1 |

This is a directory-coverage observation: it shows where active NPPES records
in this incremental file list a primary practice location. It is **not** a
measure of care access, appointment availability, provider capacity, patient
demand, or network adequacy.

## Data-completeness findings

For the 48-provider cohort, the aggregate completeness summary found:

- 0 records missing a ZIP code
- 0 records missing a phone number
- 0 records missing a taxonomy assignment

There are 23 providers with multiple taxonomy assignments. This is expected
in provider-directory data and is retained in the normalized taxonomy table.

## Limitations

- This analysis uses a weekly incremental NPPES file, not a complete statewide
  baseline. Counts and coverage patterns should not be interpreted as a full
  Massachusetts provider inventory.
- NPPES information is self-reported. It does not prove licensure,
  credentialing, network participation, or appointment availability.

## Next Improvement

Load the monthly full replacement file to establish a statewide baseline.
That baseline will make it possible to compare later weekly incremental files
against a known starting population and more reliably identify new records,
deactivations, address changes, and taxonomy changes.
