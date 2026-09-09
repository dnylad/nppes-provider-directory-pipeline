# Data plan

## Scope

This plan supports the **NPPES Provider Directory Change Pipeline** for the Massachusetts primary-care cohort. It documents the intended data design only; no source data has been downloaded or processed.

## Source and planned inputs

The source will be the CMS **NPPES Version 2 downloadable files**.

The first pipeline version will use one weekly incremental provider file as its initial input. Later versions will add these inputs:

- The monthly full replacement file
- The deactivation file
- The practice-location reference file

## Business concepts

The pipeline will retain and model the following core concepts:

- **NPI** — the provider or organization identifier
- **Entity type** — whether the NPI represents an individual or organization
- **Provider or organization name**
- **Business-practice location**
- **Taxonomy code**
- **Primary-taxonomy flag**
- **Enumeration date**
- **Deactivation date**

## Future output tables

### 1. `providers`

One row per NPI. This table will contain provider- or organization-level attributes, including entity type, name, enumeration date, deactivation date, and the primary business-practice location used for the initial Massachusetts scope.

### 2. `provider_taxonomies`

One row per NPI and taxonomy record. A provider can report more than one taxonomy, so a separate table preserves each taxonomy code and its primary-taxonomy flag without discarding secondary specialties.

### 3. `practice_locations`

One row per NPI and practice-location record. A provider or organization can report more than one practice location, so locations must not be collapsed into a single provider row.

## Massachusetts geography rule

The first version will identify Massachusetts records from the **primary business-practice location state**. A later version will incorporate non-primary practice locations so that providers with additional Massachusetts locations can also be represented.

## Version 1 Primary Care Cohort

A provider belongs in the Version 1 primary-care cohort if **any** listed NPPES taxonomy matches one of the codes below, whether or not that taxonomy is marked as the primary taxonomy.

| Taxonomy code | Specialty |
| --- | --- |
| `207Q00000X` | Family Medicine |
| `207R00000X` | Internal Medicine |
| `208D00000X` | General Practice |
| `208000000X` | Pediatrics |

## Out of Scope for Version 1

The Version 1 cohort does not include advanced practice providers, subspecialties, or non-primary practice locations. These can be added in a later version without changing the core `providers`, `provider_taxonomies`, and `practice_locations` data model.

## NPPES limitations

NPPES information is self-reported. An NPI does not prove licensure, credentialing, network participation, or whether a provider accepts new patients.
