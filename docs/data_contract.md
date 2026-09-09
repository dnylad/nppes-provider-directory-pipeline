# Data contract

## Scope

This contract defines the raw fields and validation rules for Version 1 of the Massachusetts primary-care NPPES provider pipeline. It applies to the weekly Version 2 main provider file and does not define ingestion or transformation code.

## Business-concept mapping

| Business concept | Raw NPPES field(s) |
| --- | --- |
| NPI | `NPI` |
| Entity type | `Entity Type Code` |
| Individual/provider name | `Provider Last Name (Legal Name)`, `Provider First Name`, `Provider Middle Name`, `Provider Name Prefix Text`, `Provider Name Suffix Text`, `Provider Credential Text` |
| Organization name | `Provider Organization Name (Legal Business Name)` |
| Primary practice state | `Provider Business Practice Location Address State Name` |
| ZIP code | `Provider Business Practice Location Address Postal Code` |
| Taxonomy code | `Healthcare Provider Taxonomy Code_1` through `Healthcare Provider Taxonomy Code_15` (listed exactly in [Repeating taxonomy fields](#repeating-taxonomy-fields)) |
| Primary-taxonomy indicator | `Healthcare Provider Primary Taxonomy Switch_1` through `Healthcare Provider Primary Taxonomy Switch_15` (listed exactly in [Repeating taxonomy fields](#repeating-taxonomy-fields)) |
| Enumeration date | `Provider Enumeration Date` |
| Deactivation date | `NPI Deactivation Date` |

## Required and optional fields

The following requirements apply to Version 1 processing, not necessarily to every raw NPPES record.

| Field or fields | Requirement | Reason |
| --- | --- | --- |
| `NPI` | Required | Identifies the provider record. |
| `Entity Type Code` | Required | Version 1 retains individual-provider records only. |
| `Provider Last Name (Legal Name)` and `Provider First Name` | Required for retained individual-provider records | Provide the individual provider name. |
| `Provider Organization Name (Legal Business Name)` | Optional and not used for Version 1 retention | Applies to organization records, which are out of scope unless the design explicitly expands later. |
| `Provider Business Practice Location Address State Name` | Required for Version 1 cohort inclusion | Must identify Massachusetts as the primary practice state. |
| `Provider Business Practice Location Address Postal Code` | Required for ZIP-level outputs | Must provide a usable five-digit ZIP value. |
| At least one `Healthcare Provider Taxonomy Code_1` through `Healthcare Provider Taxonomy Code_15` | Required for Version 1 cohort inclusion | At least one code must match an approved primary-care code. |
| `Provider Enumeration Date` | Optional | Validate it when present. |
| `NPI Deactivation Date` | Optional | Validate it when present. |

## Repeating taxonomy fields

NPPES stores up to 15 taxonomy slots. Version 1 must examine all of the following exact fields, not only the taxonomy marked primary.

| Slot | Taxonomy code field | Primary-taxonomy indicator field |
| --- | --- | --- |
| 1 | `Healthcare Provider Taxonomy Code_1` | `Healthcare Provider Primary Taxonomy Switch_1` |
| 2 | `Healthcare Provider Taxonomy Code_2` | `Healthcare Provider Primary Taxonomy Switch_2` |
| 3 | `Healthcare Provider Taxonomy Code_3` | `Healthcare Provider Primary Taxonomy Switch_3` |
| 4 | `Healthcare Provider Taxonomy Code_4` | `Healthcare Provider Primary Taxonomy Switch_4` |
| 5 | `Healthcare Provider Taxonomy Code_5` | `Healthcare Provider Primary Taxonomy Switch_5` |
| 6 | `Healthcare Provider Taxonomy Code_6` | `Healthcare Provider Primary Taxonomy Switch_6` |
| 7 | `Healthcare Provider Taxonomy Code_7` | `Healthcare Provider Primary Taxonomy Switch_7` |
| 8 | `Healthcare Provider Taxonomy Code_8` | `Healthcare Provider Primary Taxonomy Switch_8` |
| 9 | `Healthcare Provider Taxonomy Code_9` | `Healthcare Provider Primary Taxonomy Switch_9` |
| 10 | `Healthcare Provider Taxonomy Code_10` | `Healthcare Provider Primary Taxonomy Switch_10` |
| 11 | `Healthcare Provider Taxonomy Code_11` | `Healthcare Provider Primary Taxonomy Switch_11` |
| 12 | `Healthcare Provider Taxonomy Code_12` | `Healthcare Provider Primary Taxonomy Switch_12` |
| 13 | `Healthcare Provider Taxonomy Code_13` | `Healthcare Provider Primary Taxonomy Switch_13` |
| 14 | `Healthcare Provider Taxonomy Code_14` | `Healthcare Provider Primary Taxonomy Switch_14` |
| 15 | `Healthcare Provider Taxonomy Code_15` | `Healthcare Provider Primary Taxonomy Switch_15` |

## Version 1 filtering rules

A record is in the Version 1 cohort only when all of these conditions are met:

1. `Entity Type Code` identifies an individual provider.
2. `Provider Business Practice Location Address State Name` identifies Massachusetts as the primary practice location.
3. Any `Healthcare Provider Taxonomy Code_1` through `Healthcare Provider Taxonomy Code_15` equals one of the approved codes: `207Q00000X` (Family Medicine), `207R00000X` (Internal Medicine), `208D00000X` (General Practice), or `208000000X` (Pediatrics).

The matching taxonomy does not need to have a primary-taxonomy indicator. The indicator is retained as data, but it does not determine cohort membership.

## Data-quality rules

- `NPI` must be present and contain exactly 10 digits.
- `Entity Type Code` must contain a valid NPPES entity-type value.
- `Provider Business Practice Location Address Postal Code` must yield a usable five-digit ZIP value.
- `Provider Enumeration Date` and `NPI Deactivation Date` must be parseable as dates when present.
- All populated taxonomy codes must be retained, including codes whose corresponding `Healthcare Provider Primary Taxonomy Switch_1` through `Healthcare Provider Primary Taxonomy Switch_15` values do not identify them as primary.
- Records with incomplete business-practice addresses or telephone numbers must be **flagged, not deleted**. Missing contact detail is a data-quality condition, not an automatic reason to remove an otherwise in-scope provider.

## Entity-type boundary

The first version processes individual providers only. Organization records are excluded unless the project design explicitly expands later to include them.
