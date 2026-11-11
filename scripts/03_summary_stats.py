"""
03_summary_stats.py — District/regional summary statistics used in the briefing and appendix.
Outputs: data/processed/summary_stats.json, data/processed/table_*.csv, logs/03_summary_stats.log
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
GPKG = ROOT / "data/processed/ca17_analysis.gpkg"
OUT = ROOT / "data/processed"
EXT = ROOT / "data/extracted"
LOG = open(ROOT / "logs/03_summary_stats.log", "w")
S = {}


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")


tr = gpd.read_file(GPKG, layer="ca17_tracts_analysis")
reg = gpd.read_file(GPKG, layer="region_tracts_3county")
fac = gpd.read_file(GPKG, layer="facilities_documented")
osm = gpd.read_file(GPKG, layer="datacenters_osm_existing")
osm = osm[osm.dup_of.isna()]
ds = tr[tr.in_district_set == 1]

# ---------- reference geographies straight from the ACS extracts (state, counties, 119th-Congress CD 17)
def acs_rows(folder, table, ids):
    d = pd.read_csv(EXT / folder / f"ACSDT5Y2024.{table}-Data.csv", dtype=str, skiprows=[1])
    return d[d.GEO_ID.isin(ids)].set_index("GEO_ID")


IDS = {"California": "0400000US06", "Santa Clara County": "0500000US06085", "Alameda County": "0500000US06001",
       "San Mateo County": "0500000US06081", "CD-17 (119th Congress, 2024 ACS)": "5001900US0617"}
inc = acs_rows("Median Household Income", "B19013", IDS.values())
rent = acs_rows("Median Gross Rent", "B25064", IDS.values())
rb = acs_rows("Gross Rent as % of HH Income", "B25070", IDS.values())
ref = []
for name, gid in IDS.items():
    if gid not in inc.index:
        log("Reference geography not in extract:", name, gid)
        continue
    b = rb.loc[gid]
    f = lambda k: float(b[k])
    comp = f("B25070_001E") - f("B25070_011E")
    b30 = sum(f(f"B25070_{k:03d}E") for k in (7, 8, 9, 10))
    ref.append({"geography": name, "GEO_ID": gid, "acs_name": inc.loc[gid, "NAME"],
                "median_hh_income": float(inc.loc[gid, "B19013_001E"]), "mhi_moe": float(inc.loc[gid, "B19013_001M"]),
                "median_gross_rent": float(rent.loc[gid, "B25064_001E"]), "mgr_moe": float(rent.loc[gid, "B25064_001M"]),
                "renter_hh_computed": comp, "pct_burden30": 100 * b30 / comp, "pct_burden50": 100 * f("B25070_010E") / comp})
ref = pd.DataFrame(ref)
log("Reference geographies:\n" + ref.round(1).to_string())
ref.to_csv(OUT / "table_reference_geographies.csv", index=False)


# ---------- pooled district-set rent burden (sum of tract counts) with MOE
def pooled(df):
    n30, d = df.burden30_n.sum(), df.rent_hh_computed.sum()
    n50 = df.burden50_n.sum()
    m30, md, m50 = np.sqrt((df.burden30_moe ** 2).sum()), np.sqrt((df.rent_hh_computed_moe ** 2).sum()), np.sqrt((df.burden50_moe ** 2).sum())
    def pm(n, mn):
        p = n / d
        r = mn ** 2 - p ** 2 * md ** 2
        return 100 * p, 100 * (np.sqrt(r) if r > 0 else np.sqrt(mn ** 2 + p ** 2 * md ** 2)) / d
    p30, e30 = pm(n30, m30)
    p50, e50 = pm(n50, m50)
    return {"renter_hh_computed": d, "pct_burden30": p30, "pct_burden30_moe": e30, "pct_burden50": p50, "pct_burden50_moe": e50,
            "n_burden30": n30}


S["district_set"] = {"n_tracts": int(len(ds)), "pop_ces2024": float(ds.ces_ACS2024Pop.sum()),
                     "by_county_tracts": ds.COUNTYFP.value_counts().to_dict(), **pooled(ds)}
S["region_3county"] = {"n_tracts": int(len(reg)), **pooled(reg)}
S["overlap_classes"] = tr.overlap_class.value_counts().sort_index().to_dict()
log("\nDistrict set pooled burden:", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in S["district_set"].items()})
log("Region pooled burden:", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in S["region_3county"].items()})

# ---------- tract distributions (medians cannot be pooled; report distribution of tract medians)
def dist(s):
    s = s.dropna()
    return {"n": int(len(s)), "min": float(s.min()), "p25": float(s.quantile(.25)), "median": float(s.median()),
            "p75": float(s.quantile(.75)), "max": float(s.max())}


S["tract_mhi"] = dist(ds.mhi)
S["tract_mgr"] = dist(ds.mgr)
S["tract_burden30"] = dist(ds.pct_burden30[ds.rent_hh_computed >= 50])
S["mhi_topcoded_n"] = int((ds.mhi_flag == "top-coded").sum())
S["mgr_topcoded_n"] = int((ds.mgr_flag == "top-coded").sum())
S["burden30_cv_gt40_n"] = int((ds.pct_burden30_cv > 40).sum())
S["burden30_tracts_ge50pct"] = int((ds.pct_burden30 >= 50).sum())
S["burden30_tracts_ge50pct_lowerbound"] = int(((ds.pct_burden30 - ds.pct_burden30_moe) >= 50).sum())
log("\nTract MHI:", S["tract_mhi"], "top-coded:", S["mhi_topcoded_n"])
log("Tract MGR:", S["tract_mgr"], "top-coded:", S["mgr_topcoded_n"])
log("Tract burden30:", S["tract_burden30"], " CV>40%:", S["burden30_cv_gt40_n"],
    " tracts >=50% burdened:", S["burden30_tracts_ge50pct"], " (lower 90% bound >=50%:", S["burden30_tracts_ge50pct_lowerbound"], ")")

# ---------- CalEnviroScreen
S["ces"] = {"tract_CIscoreP": dist(ds.ces_CIscoreP), "n_top25": int((ds.ces_CIscoreP >= 75).sum()),
            "pop_top25": float(ds.loc[ds.ces_CIscoreP >= 75, "ces_ACS2024Pop"].sum()),
            "n_ge50": int((ds.ces_CIscoreP >= 50).sum()),
            "region_n_top25": int((reg.ces_CIscoreP >= 75).sum())}
ind = ["ozoneP", "pmP", "dieselP", "trafficP", "RSEIhazP", "cleanupsP", "gwthreatsP", "hazP", "swisP", "iwbP",
       "drinkP", "leadP", "pestP", "SmATSP", "asthmaP", "lbwP", "cvdP", "povP", "housingBP", "lingP", "unempP", "eduP"]
w = ds.ces_ACS2024Pop
indt = pd.DataFrame({"indicator": ind,
                     "median_tract_pctile": [ds[f"ces_{c}"].median() for c in ind],
                     "pop_weighted_mean_pctile": [np.average(ds[f"ces_{c}"].dropna(), weights=w[ds[f"ces_{c}"].notna()]) for c in ind],
                     "share_tracts_ge75": [(ds[f"ces_{c}"] >= 75).mean() * 100 for c in ind]}).sort_values("median_tract_pctile", ascending=False)
log("\nCES indicators (district set, statewide percentiles):\n" + indt.round(1).to_string(index=False))
indt.to_csv(OUT / "table_ces_indicators_district.csv", index=False)
S["ces_indicators_top"] = indt.head(6).round(1).to_dict("records")
top_ces = ds.sort_values("ces_CIscoreP", ascending=False)[["GEOID", "ces_approx_loc", "ces_CIscoreP", "ces_PollutionP", "ces_PopCharP",
                                                           "pct_burden30", "pct_burden30_moe", "mhi", "ces_ACS2024Pop"]].head(12)
log("Highest-CES district tracts:\n" + top_ces.round(1).to_string(index=False))
top_ces.to_csv(OUT / "table_top_ces_tracts.csv", index=False)

# ---------- association (descriptive only)
v = ds[(ds.rent_hh_computed >= 50)].dropna(subset=["pct_burden30", "ces_CIscoreP"])
rho, p = spearmanr(v.pct_burden30, v.ces_CIscoreP)
rho2, p2 = spearmanr(ds.dropna(subset=["mhi", "ces_CIscoreP"]).mhi, ds.dropna(subset=["mhi", "ces_CIscoreP"]).ces_CIscoreP)
S["spearman_burden_ces"] = {"rho": rho, "p": p, "n": int(len(v))}
S["spearman_mhi_ces"] = {"rho": rho2, "p": p2}
log(f"\nSpearman burden30 vs CES pctile (district tracts, n={len(v)}): rho={rho:.2f} p={p:.3g}; MHI vs CES rho={rho2:.2f}")

# ---------- bivariate screen
S["bivar_counts_district"] = ds.bivar.value_counts().to_dict()
scr = ds[ds.screen_overlap == 1]
S["screen_overlap_n"] = int(len(scr))
S["screen_overlap_pop"] = float(scr.ces_ACS2024Pop.sum())
S["screen_overlap_names"] = sorted(scr.ces_approx_loc.dropna().unique().tolist())
log("\nBivariate classes (district set):", S["bivar_counts_district"])
log("High-high (top regional tercile on both) tracts:", len(scr), "pop", scr.ces_ACS2024Pop.sum(), S["screen_overlap_names"])
scr[["GEOID", "ces_approx_loc", "overlap_share", "pct_burden30", "pct_burden30_moe", "burden30_rel", "ces_CIscoreP",
     "ces_PollutionP", "ces_PopCharP", "mhi", "ces_ACS2024Pop"]].round(1).to_csv(OUT / "table_screen_overlap_tracts.csv", index=False)

# ---------- facilities relative to the screen
d = fac[fac.facility_type == "data_center"]
S["fac"] = {"n_documented_dc": int(len(d)), "n_dc_in_ca17": int(d.in_ca17.sum()),
            "n_dc_proposed": int((d.status_class == "Proposed - under review").sum()),
            "n_dc_in_ca17_proposed": int(((d.status_class == "Proposed - under review") & (d.in_ca17 == 1)).sum()),
            "n_leu": int((fac.facility_type != "data_center").sum()),
            "n_leu_in_ca17": int(((fac.facility_type != "data_center") & (fac.in_ca17 == 1)).sum()),
            "mw_disclosed_in_ca17": float(d.loc[d.in_ca17 == 1, "power_mw"].sum()),
            "n_mw_disclosed_in_ca17": int(d.loc[d.in_ca17 == 1, "power_mw"].notna().sum()),
            "dc_in_ces_top25": int((d.ces_CIscoreP >= 75).sum()),
            "dc_in_highhigh": int((d.bivar == "3-3").sum()),
            "dc_within_1km_ca17": int(((d.in_ca17 == 0) & (d.dist_ca17_m <= 1000)).sum()),
            "osm_unique_region": int(osm.host_tract.notna().sum()), "osm_in_ca17": int(osm.in_ca17.sum())}
# Distance from each documented DC to nearest high-high screen tract (district or region)
hh = reg[reg.screen_overlap == 1]
d = d.assign(dist_highhigh_m=d.geometry.apply(lambda g: hh.distance(g).min()).round(0))
S["fac"]["dc_within_1km_highhigh"] = int((d.dist_highhigh_m <= 1000).sum())
log("\nFacility summary:", S["fac"])
log(d[["inv_id", "facility_name", "status_class", "in_ca17", "dist_ca17_m", "ces_CIscoreP", "pct_burden30", "bivar",
       "dist_highhigh_m", "pop_1km_est"]].to_string())
d.drop(columns="geometry").to_csv(OUT / "table_documented_dc_context.csv", index=False)

# OSM host tracts within CA-17 vs other district tracts
ds_ids = set(ds.GEOID)
regd = reg[reg.GEOID_std.isin(ds_ids)]
cmp = regd.groupby(regd.osm_dc_n > 0).agg(n=("GEOID_std", "size"), ces_med=("ces_CIscoreP", "median"),
                                          poll_med=("ces_PollutionP", "median"), popchar_med=("ces_PopCharP", "median"),
                                          burden_med=("pct_burden30", "median"), pop=("ces_ACS2024Pop", "sum"),
                                          dcs=("osm_dc_n", "sum"))
log("\nCA-17 tracts hosting existing (OSM) DCs vs not:\n" + cmp.round(1).to_string())
S["osm_host_vs_not_district"] = cmp.round(1).reset_index().to_dict("records")

json.dump(S, open(OUT / "summary_stats.json", "w"), indent=1, default=float)
LOG.close()
