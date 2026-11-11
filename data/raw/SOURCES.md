# Raw inputs (unmodified)

| File | Source | Notes |
|---|---|---|
| `CA17_Study_Area.gpkg` | U.S. Census Bureau, 2026 TIGER/Line, 120th Congress congressional districts | 1 feature, GEOID 0617, EPSG:4269 |
| `CA17_Census_Tracts.gpkg` | U.S. Census Bureau, 2026 TIGER/Line tracts (2020 vintage), selected by *Intersects* with CA-17 | 202 features |
| `Median Household Income.zip` | data.census.gov, ACS 2020–2024 5-year, table B19013 | all U.S. summary levels |
| `Median Gross Rent.zip` | data.census.gov, ACS 2020–2024 5-year, table B25064 | |
| `Gross Rent as % of HH Income.zip` | data.census.gov, ACS 2020–2024 5-year, table B25070 | |
| `GrossRentas%ofincome.gpkg` | attribute-only copy of the B25070 CSV | not used (duplicate) |
| `calenviroscreen50results_f_070126.shp.zip` | OEHHA, CalEnviroScreen 5.0 results shapefile (June 2026) | 9,106 tracts |
| `CaliforniaEA_ada.csv` | California Energy Commission, Energy Equity Indicators: energy affordability by tract and tenure (**draft**, "Data is NOT final") | context only |
| `Alameda Housing Data.xlsx`, `SC Housing Data.xlsx` | HCD Housing Element Sites Inventory extract | byte-identical files covering the City of Alameda (outside CA-17); not used |

Run `scripts/00_extract.sh` to unzip the archives into `data/extracted/`.
