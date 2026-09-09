# Source log

## Initial source file

- **ZIP filename:** `NPPES_Data_Dissemination_080326_080926_Weekly_V2.zip`
- **Download date:** 2026-09-09
- **Source URL:** [CMS NPPES NPI Files](https://download.cms.gov/nppes/NPI_Files.html)
- **File type:** Version 2 weekly incremental file

This weekly incremental file is the project’s starting sample. It will later be compared with a baseline monthly full-replacement file to identify provider-directory changes.

## Archive contents

| File | Role |
| --- | --- |
| `npidata_pfile_20260803-20260809.csv` | Main provider data file containing NPI records and provider-level attributes. |
| `npidata_pfile_20260803-20260809_fileheader.csv` | Header/reference file for the main provider data columns. |
| `pl_pfile_20260803-20260809.csv` | Practice-location file containing location records associated with NPIs. |
| `pl_pfile_20260803-20260809_fileheader.csv` | Header/reference file for practice-location columns. |
| `othername_pfile_20260803-20260809.csv` | Other-name file containing alternate provider or organization names. |
| `othername_pfile_20260803-20260809_fileheader.csv` | Header/reference file for other-name columns. |
| `endpoint_pfile_20260803-20260809.csv` | Endpoint file containing electronic service endpoint information associated with NPIs. |
| `endpoint_pfile_20260803-20260809_fileheader.csv` | Header/reference file for endpoint columns. |
| `NPPES_Data_Dissemination_CodeValues.pdf` | Reference for coded field values. |
| `NPPES_Data_Dissemination_Readme_v.2.pdf` | CMS Read Me with delivery and file-content guidance. |

## Main provider file headers

The main provider file is `npidata_pfile_20260803-20260809.csv`. Its first 15 headers are:

1. `NPI`
2. `Entity Type Code`
3. `Replacement NPI`
4. `Employer Identification Number (EIN)`
5. `Provider Organization Name (Legal Business Name)`
6. `Provider Last Name (Legal Name)`
7. `Provider First Name`
8. `Provider Middle Name`
9. `Provider Name Prefix Text`
10. `Provider Name Suffix Text`
11. `Provider Credential Text`
12. `Provider Other Organization Name`
13. `Provider Other Organization Name Type Code`
14. `Provider Other Last Name`
15. `Provider Other First Name`

## Version-control handling

Raw NPPES data is intentionally excluded from GitHub. This document records source metadata only and does not include provider records or other identifiable details.
