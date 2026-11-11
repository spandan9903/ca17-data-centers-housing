"""
01_prepare_data.py — Build cleaned, joined analytical layers for CA-17.

Inputs  : data/raw/* (read-only originals) and data/extracted/* (unzipped archives)
Outputs : data/processed/ca17_analysis.gpkg  (layers listed at bottom)
          data/processed/*.csv               (join-validation and summary tables)
          logs/01_prepare_data.log

Run with QGIS's bundled Python after `source scripts/env.sh`:
    $QGIS_APP/MacOS/python -I scripts/01_prepare_data.py   (or without -I if PYTHONPATH needed)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW, EXT, OUT = ROOT / "data/raw", ROOT / "data/extracted", ROOT / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "logs").mkdir(exist_ok=True)
GPKG = OUT / "ca17_analysis.gpkg"
LOG = open(ROOT / "logs/01_prepare_data.log", "w")
CRS_AREA = "EPSG:3310"  # California Albers (NAD83) — equal-area, metres
REGION_COUNTIES = {"001": "Alameda", "085": "Santa Clara", "081": "San Mateo"}


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")


# ---------------------------------------------------------------- 1. geography
cd = gpd.read_file(RAW / "CA17_Study_Area.gpkg")
tr = gpd.read_file(RAW / "CA17_Census_Tracts.gpkg")
log("District features:", len(cd), "GEOID:", list(cd.GEOID), "CRS:", cd.crs.to_string())
log("Tract features:", len(tr), "unique GEOID:", tr.GEOID.nunique(), "CRS:", tr.crs.to_string())
assert len(cd) == 1 and cd.GEOID.iloc[0] == "0617"
assert tr.GEOID.str.len().eq(11).all()

cd_a = cd.to_crs(CRS_AREA)
tr_a = tr.to_crs(CRS_AREA)
log("Invalid geometries — district:", (~cd_a.is_valid).sum(), " tracts:", (~tr_a.is_valid).sum())
tr_a["geometry"] = tr_a.geometry.make_valid()
cd_geom = cd_a.geometry.make_valid().iloc[0]

tr_a["tract_area_km2"] = tr_a.geometry.area / 1e6
tr_a["tract_land_km2"] = tr_a["ALAND"] / 1e6
tr_a["overlap_km2"] = tr_a.geometry.intersection(cd_geom).area / 1e6
tr_a["overlap_share"] = tr_a["overlap_km2"] / tr_a["tract_area_km2"]


def overlap_class(s):
    if s >= 0.90:
        return "1_within (>=90%)"
    if s >= 0.50:
        return "2_majority (50-90%)"
    if s >= 0.05:
        return "3_minority (5-50%)"
    return "4_sliver (<5%)"


tr_a["overlap_class"] = tr_a["overlap_share"].apply(overlap_class)
# Analytical rule: tracts with >=50% of their area in CA-17 form the "district analysis set".
# Minority/sliver tracts are retained (flagged) for regional context but excluded from
# district-level aggregates, because their residents are mostly outside CA-17.
tr_a["in_district_set"] = (tr_a["overlap_share"] >= 0.50).astype(int)
log("\nOverlap classes:\n", tr_a["overlap_class"].value_counts().sort_index().to_string())
log("Tracts by county x class:\n", pd.crosstab(tr_a.COUNTYFP, tr_a.overlap_class).to_string())
log("Sum of overlap area (km2):", round(tr_a.overlap_km2.sum(), 2),
    " district area (km2):", round(cd_geom.area / 1e6, 2))

# ----------------------------------------------------------- 2. ACS tables
NUMRE = re.compile(r"^-?\d+(\.\d+)?$")


def acs_num(series):
    """Convert ACS string values to float; return (values, flag) where flag records
    top/bottom-coding or suppression annotations (e.g. '250,000+', '-', '***', 'N')."""
    s = series.astype(str).str.strip()
    flag = pd.Series("", index=s.index)
    top = s.str.endswith("+")
    bot = s.str.endswith("-") & (s.str.len() > 1)
    clean = s.str.replace(",", "", regex=False).str.rstrip("+").str.rstrip("-")
    val = pd.to_numeric(clean.where(clean.str.match(NUMRE)), errors="coerce")
    flag[top] = "top-coded"
    flag[bot] = "bottom-coded"
    flag[val.isna()] = "suppressed/NA(" + s[val.isna()] + ")"
    return val, flag


def load_acs(folder, table):
    f = EXT / folder / f"ACSDT5Y2024.{table}-Data.csv"
    df = pd.read_csv(f, dtype=str, skiprows=[1])  # row 2 = human-readable labels
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    n_all = len(df)
    df = df[df.GEO_ID.str.startswith("1400000US06")].copy()  # CA census tracts only
    df["GEOID_std"] = df.GEO_ID.str[-11:]
    log(f"{table}: {n_all} rows nationally (all summary levels) -> {len(df)} CA tracts")
    return df


inc = load_acs("Median Household Income", "B19013")
inc["mhi"], inc["mhi_flag"] = acs_num(inc.B19013_001E)
inc["mhi_moe"], inc["mhi_moe_flag"] = acs_num(inc.B19013_001M)

rent = load_acs("Median Gross Rent", "B25064")
rent["mgr"], rent["mgr_flag"] = acs_num(rent.B25064_001E)
rent["mgr_moe"], rent["mgr_moe_flag"] = acs_num(rent.B25064_001M)

rb = load_acs("Gross Rent as % of HH Income", "B25070")
for i in range(1, 12):
    k = f"{i:03d}"
    rb[f"b{k}"], _ = acs_num(rb[f"B25070_{k}E"])
    rb[f"b{k}_m"], _ = acs_num(rb[f"B25070_{k}M"])
# Denominator: renter households for whom the ratio is computed (total minus "Not computed")
rb["rent_hh_total"] = rb["b001"]
rb["rent_hh_computed"] = rb["b001"] - rb["b011"]
rb["rent_hh_computed_moe"] = np.sqrt(rb["b001_m"] ** 2 + rb["b011_m"] ** 2)
rb["burden30_n"] = rb[["b007", "b008", "b009", "b010"]].sum(axis=1)
rb["burden30_moe"] = np.sqrt((rb[["b007_m", "b008_m", "b009_m", "b010_m"]] ** 2).sum(axis=1))
rb["burden50_n"] = rb["b010"]
rb["burden50_moe"] = rb["b010_m"]


def prop_moe(num, num_moe, den, den_moe):
    """Census Bureau approximation for MOE of a proportion (ACS Handbook, 2020, eq. 4);
    falls back to the ratio formula when the radicand is negative."""
    p = num / den
    rad = num_moe ** 2 - (p ** 2) * den_moe ** 2
    rad_ratio = num_moe ** 2 + (p ** 2) * den_moe ** 2
    moe = np.where(rad >= 0, np.sqrt(rad.clip(lower=0)), np.sqrt(rad_ratio)) / den
    return p, moe


den = rb["rent_hh_computed"].where(rb["rent_hh_computed"] > 0)
rb["pct_burden30"], rb["pct_burden30_moe"] = prop_moe(rb.burden30_n, rb.burden30_moe, den, rb.rent_hh_computed_moe)
rb["pct_burden50"], rb["pct_burden50_moe"] = prop_moe(rb.burden50_n, rb.burden50_moe, den, rb.rent_hh_computed_moe)
for c in ["pct_burden30", "pct_burden30_moe", "pct_burden50", "pct_burden50_moe"]:
    rb[c] = rb[c] * 100

acs = (inc[["GEOID_std", "GEO_ID", "NAME", "mhi", "mhi_moe", "mhi_flag"]]
       .merge(rent[["GEOID_std", "mgr", "mgr_moe", "mgr_flag"]], on="GEOID_std", how="outer", validate="1:1")
       .merge(rb[["GEOID_std", "rent_hh_total", "rent_hh_computed", "rent_hh_computed_moe",
                  "burden30_n", "burden30_moe", "burden50_n", "burden50_moe",
                  "pct_burden30", "pct_burden30_moe", "pct_burden50", "pct_burden50_moe"]],
              on="GEOID_std", how="outer", validate="1:1"))
acs = acs.rename(columns={"GEO_ID": "acs_GEO_ID", "NAME": "acs_NAME"})


# Reliability: coefficient of variation (CV = (MOE/1.645)/estimate). >40% = low reliability.
def cv(est, moe):
    return (moe / 1.645) / est.where(est > 0) * 100


acs["mhi_cv"] = cv(acs.mhi, acs.mhi_moe)
acs["mgr_cv"] = cv(acs.mgr, acs.mgr_moe)
acs["pct_burden30_cv"] = cv(acs.pct_burden30, acs.pct_burden30_moe)


def rel(c):
    return np.select([c.isna(), c <= 15, c <= 30, c <= 40], ["n/a", "high", "medium", "fair"], "low")


acs["mhi_rel"] = rel(acs.mhi_cv)
acs["mgr_rel"] = rel(acs.mgr_cv)
acs["burden30_rel"] = rel(acs.pct_burden30_cv)
acs.to_csv(OUT / "acs_ca_tracts_clean.csv", index=False)

# ----------------------------------------------------------- 3. CalEnviroScreen 5.0
ces_path = next((EXT / "calenviroscreen50results_f_070126.shp").rglob("*.shp"))
ces = gpd.read_file(ces_path)
log(f"\nCES 5.0: {len(ces)} tracts, CRS {ces.crs.to_string()}")
ces["GEOID_std"] = ces["tract"].round().astype("int64").astype(str).str.zfill(11)
num_cols = ces.select_dtypes("number").columns
n_neg = {c: int((ces[c] <= -999).sum()) for c in num_cols if (ces[c] <= -999).any()}
log("CES fields with -999 (no data) codes:", n_neg)
ces[num_cols] = ces[num_cols].where(ces[num_cols] > -999)  # -999 -> NaN
CES_KEEP = ["GEOID_std", "approx_loc", "county", "ACS2024Pop", "CIscore", "CIscoreP",
            "Pollution", "PollutionS", "PollutionP", "PopChar", "PopCharSco", "PopCharP",
            "ozoneP", "pmP", "dieselP", "trafficP", "RSEIhazP", "cleanupsP", "gwthreatsP",
            "hazP", "swisP", "iwbP", "drinkP", "leadP", "pestP", "SmATSP",
            "asthmaP", "lbwP", "cvdP", "povP", "housingBP", "lingP", "unempP", "eduP"]
ces_attr = ces[CES_KEEP].rename(columns={c: f"ces_{c}" for c in CES_KEEP if c != "GEOID_std"})

# ----------------------------------------------------------- 4. CEC energy affordability (draft)
ea = pd.read_csv(RAW / "CaliforniaEA_ada.csv", dtype={"FIP": str})
ea["GEOID_std"] = ea.FIP.str.zfill(11)
log(f"\nEnergy affordability CSV: {len(ea)} rows, {ea.GEOID_std.nunique()} tracts, tenant types {ea['Tenant Type'].value_counts().to_dict()}")
ea_w = ea.pivot_table(index="GEOID_std", columns="Tenant Type",
                      values=["Energy Burden", "Household Energy Costs", "Energy Affordability Index"])
ea_w.columns = [f"ea_{b.replace(' ', '')}_{a.replace(' ', '').replace('Energy', 'E').replace('Household', 'HH')}"
                for a, b in ea_w.columns]
ea_w = ea_w.reset_index()

# ----------------------------------------------------------- 5. joins + validation
val_rows = []


def join_report(name, left_ids, right_ids):
    L, R = set(left_ids), set(right_ids)
    miss = sorted(L - R)
    val_rows.append({"join": name, "left_n": len(L), "matched": len(L & R),
                     "unmatched_left": len(miss), "unmatched_ids": ";".join(miss)})
    log(f"JOIN {name}: {len(L & R)}/{len(L)} matched; unmatched: {miss}")


ids = tr_a.GEOID
join_report("tracts->ACS B19013/B25064/B25070", ids, acs.GEOID_std)
join_report("tracts->CES5.0", ids, ces_attr.GEOID_std)
join_report("tracts->CEC energy affordability", ids, ea_w.GEOID_std)

ca17 = (tr_a.merge(acs, left_on="GEOID", right_on="GEOID_std", how="left", validate="1:1")
        .drop(columns="GEOID_std")
        .merge(ces_attr, left_on="GEOID", right_on="GEOID_std", how="left", validate="1:1")
        .drop(columns="GEOID_std")
        .merge(ea_w, left_on="GEOID", right_on="GEOID_std", how="left", validate="1:1")
        .drop(columns="GEOID_std"))
ca17["GEOID_std"] = ca17["GEOID"]
assert len(ca17) == 202

# Missing-value report for the 202 tracts
miss_cols = ["mhi", "mgr", "pct_burden30", "pct_burden50", "ces_CIscoreP", "ces_PollutionP", "ces_PopCharP",
             "ea_REN_EBurden"]
miss = pd.DataFrame({c: [int(ca17[c].isna().sum()), int(ca17.loc[ca17.in_district_set == 1, c].isna().sum())]
                     for c in miss_cols if c in ca17}, index=["all_202", "district_set"]).T
log("\nMissing values:\n" + miss.to_string())
miss.to_csv(OUT / "missing_values_ca17.csv")
flags = ca17.loc[(ca17.mhi_flag != "") | (ca17.mgr_flag != ""), ["GEOID", "overlap_class", "mhi", "mhi_flag", "mgr", "mgr_flag", "rent_hh_total"]]
log("ACS annotation flags (top-coded / suppressed):\n" + flags.to_string())
flags.to_csv(OUT / "acs_flags_ca17.csv", index=False)

# ----------------------------------------------------------- 6. region (Alameda/Santa Clara/San Mateo)
# CES geometries are 2020 tract polygons statewide; used as the regional tract frame.
ces_geo = ces[["GEOID_std", "geometry"]].copy()
ces_geo["COUNTYFP"] = ces_geo.GEOID_std.str[2:5]
reg = ces_geo[ces_geo.COUNTYFP.isin(REGION_COUNTIES)].copy()
reg["county_name"] = reg.COUNTYFP.map(REGION_COUNTIES)
join_report("region tracts (CES geom)->ACS", reg.GEOID_std, acs.GEOID_std)
reg = (reg.merge(acs, on="GEOID_std", how="left", validate="1:1")
       .merge(ces_attr, on="GEOID_std", how="left", validate="1:1"))
reg["in_ca17_tractset"] = reg.GEOID_std.isin(ca17.GEOID).astype(int)
reg = reg.merge(ca17[["GEOID", "overlap_share", "in_district_set"]], left_on="GEOID_std",
                right_on="GEOID", how="left").drop(columns="GEOID")
reg["overlap_share"] = reg.overlap_share.fillna(0)
reg["in_district_set"] = reg.in_district_set.fillna(0).astype(int)
log(f"Region tracts: {len(reg)} ({reg.county_name.value_counts().to_dict()})")

# County polygons (dissolved from CES tracts) for county-composition check
counties = ces.assign(COUNTYFP=ces.GEOID_std.str[2:5]).dissolve(by="county", as_index=False)[["county", "COUNTYFP", "geometry"]]
cd_cty = gpd.overlay(cd_a[["GEOID", "geometry"]], counties.to_crs(CRS_AREA), how="intersection", keep_geom_type=True)
cd_cty["area_km2"] = cd_cty.area / 1e6
cd_cty["share"] = cd_cty.area_km2 / cd_cty.area_km2.sum()
log("\nCA-17 area by county (CES-tract-derived county polygons):\n" +
    cd_cty[["county", "area_km2", "share"]].sort_values("area_km2", ascending=False).to_string())
cd_cty.drop(columns="geometry").to_csv(OUT / "ca17_county_composition.csv", index=False)

# District-set population and county split (CES ACS2024Pop is total pop per tract)
ca17_pop = ca17.loc[ca17.in_district_set == 1].groupby("COUNTYFP")["ces_ACS2024Pop"].sum()
log("District-set tract population by county (ACS 2024 via CES):", ca17_pop.to_dict())

# ----------------------------------------------------------- 7. classifications for maps
# Regional (3-county) terciles are used for the bivariate screen so that "high" means high
# relative to the surrounding labour/housing market, not relative to CA-17 only.
def tercile(s, ref):
    q = ref.quantile([1 / 3, 2 / 3]).values
    return pd.cut(s, [-np.inf, q[0], q[1], np.inf], labels=[1, 2, 3]).astype("float")


ref_b = reg.pct_burden30.where(reg.rent_hh_computed >= 50)  # ignore tiny renter bases
ref_c = reg.ces_CIscoreP
for df in (ca17, reg):
    df["burden_reliable"] = ((df.rent_hh_computed >= 50) & (df.pct_burden30_cv <= 40)).astype(int)
    df["burden_t"] = tercile(df.pct_burden30.where(df.rent_hh_computed >= 50), ref_b)
    df["ces_t"] = tercile(df.ces_CIscoreP, ref_c)
    df["bivar"] = (df.burden_t.astype("Int64").astype(str) + "-" + df.ces_t.astype("Int64").astype(str)).where(
        df.burden_t.notna() & df.ces_t.notna(), "NA")
    df["ces_top25_state"] = (df.ces_CIscoreP >= 75).astype(int)  # SB 535 style threshold
    df["burden_ge50pct_hh"] = (df.pct_burden30 >= 50).astype(int)
    df["screen_overlap"] = ((df.burden_t == 3) & (df.ces_t == 3)).astype(int)
log("Regional tercile cut points — % rent-burdened (30%+):", ref_b.quantile([1 / 3, 2 / 3]).round(1).tolist(),
    " CES percentile:", ref_c.quantile([1 / 3, 2 / 3]).round(1).tolist())

# ----------------------------------------------------------- 8. write outputs
pd.DataFrame(val_rows).to_csv(OUT / "join_validation.csv", index=False)
if GPKG.exists():
    GPKG.unlink()
cd_a.to_file(GPKG, layer="ca17_district_120th", driver="GPKG")
ca17.to_file(GPKG, layer="ca17_tracts_analysis", driver="GPKG")
reg.to_file(GPKG, layer="region_tracts_3county", driver="GPKG")
counties[counties.COUNTYFP.isin(REGION_COUNTIES)].to_crs(CRS_AREA).to_file(GPKG, layer="region_counties", driver="GPKG")
ces.to_crs(CRS_AREA).loc[ces.GEOID_std.str[2:5].isin(REGION_COUNTIES)].to_file(GPKG, layer="ces50_region_full", driver="GPKG")
ca17.drop(columns="geometry").to_csv(OUT / "ca17_tracts_analysis.csv", index=False)
log("\nWrote", GPKG)
LOG.close()
