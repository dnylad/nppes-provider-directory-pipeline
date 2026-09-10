# Change report example

## Snapshots compared

This Gold aggregate report compares two Silver primary-care snapshots.

- Older weekly incremental snapshot: `20260803_20260809`
- Newer weekly incremental snapshot: `20260831_20260906`

## Aggregate comparison

| Change category | Count |
| --- | ---: |
| Newly observed NPIs | 27 |
| NPIs not observed in newer snapshot | 48 |
| Deactivation-status changes | 0 |
| Confirmed newly deactivated NPIs | 0 |
| Primary ZIP-code changes | 0 |
| Taxonomy-set changes | 0 |

## Interpretation

This weekly-to-weekly comparison found no shared primary-care provider records
with a changed deactivation status, primary ZIP code, or taxonomy set. The
observed differences are limited to records present in one weekly extract but
not the other.

> **Important limitation:** Both inputs are weekly incremental files, not
> complete statewide snapshots. “Newly observed” and “not observed” do not
> mean statewide provider additions or removals. File presence alone cannot
> establish market entry, directory removal, or provider availability.

## Next improvement

Use a monthly full replacement file to establish a statewide baseline, then
compare later weekly updates against that baseline. This will support more
reliable interpretation of newly observed records, deactivations, address
changes, and taxonomy changes.
