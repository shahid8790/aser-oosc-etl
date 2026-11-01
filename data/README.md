# Data

The raw data is **not included** in this repository, on purpose:

- The household table contains the names of household heads and surveyors. Personal data does not belong in a public repo.
- The data belongs to ASER Pakistan (Idara-e-Taleem-o-Aagahi), not to this project.

## How to get it

ASER makes its survey data available for free public use and asks users to fill in a short form for their records. Request the **ASER Pakistan 2012** data from ASER Pakistan (aserpakistan.org) and credit them in anything you publish.

## Expected files in `data/raw/`

```
0tblProvince.xlsx      1tblDistricts.xlsx     2tblVillages.xlsx
3VillageMapSurvey.xlsx 4Household.xlsx        5tlbHHChild.xlsx
6Mother_Data.xlsx      7Pvt_School.xlsx       8Gov_School.xlsx
```

`1_extract.py` checks for all nine files and tells you which are missing.
