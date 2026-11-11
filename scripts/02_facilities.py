"""
02_facilities.py — Geocode the documented facility inventory, clean OSM existing data centers,
and attach tract context (CES 5.0, rent burden) and proximity measures.

Inputs : data/external/inventory/facility_inventory_sources.csv  (hand-transcribed from official pages)
         data/external/osm/overpass_datacenters_raw.json        (Overpass API, telecom/building=data_center)
         data/processed/ca17_analysis.gpkg                      (from 01_prepare_data.py)
Outputs: layers added to ca17_analysis.gpkg; data/processed/facilities_*.csv; logs/02_facilities.log
Geocoder: U.S. Census Bureau Geocoder (benchmark Public_AR_Current) — cached in data/external/inventory/geocode_cache.json
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/external/inventory"
GPKG = ROOT / "data/processed/ca17_analysis.gpkg"
OUT = ROOT / "data/processed"
LOG = open(ROOT / "logs/02_facilities.log", "w")
CRS = "EPSG:3310"


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")


# ------------------------------------------------------------------ geocoding
cache_f = INV / "geocode_cache.json"
cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}


def census_geocode(addr):
    if addr in cache:
        return cache[addr]
    r = requests.get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                     params={"address": addr, "benchmark": "Public_AR_Current", "format": "json"}, timeout=60)
    m = r.json()["result"]["addressMatches"]
    res = None
    if m:
        res = {"lon": m[0]["coordinates"]["x"], "lat": m[0]["coordinates"]["y"],
               "matched": m[0]["matchedAddress"], "n_matches": len(m), "method": "Census Geocoder (address range interpolation)"}
    cache[addr] = res
    time.sleep(0.5)
    return res


def osm_intersection(a, b, bbox="37.38,-121.96,37.41,-121.92"):
    """Coordinates of the node shared by two named OSM streets (Overpass)."""
    key = f"INTERSECTION:{a}&{b}"
    if key in cache:
        return cache[key]
    q = f"""[out:json][timeout:60];
    way["name"="{a}"]({bbox})->.a; way["name"="{b}"]({bbox})->.b;
    node(w.a)->.na; node(w.b)->.nb; node.na.nb; out;"""
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q},
                      headers={"User-Agent": "CA17-research-script/1.0"}, timeout=90)
    els = r.json().get("elements", [])
    res = None
    if els:
        res = {"lon": float(np.mean([e["lon"] for e in els])), "lat": float(np.mean([e["lat"] for e in els])),
               "matched": f"{a} & {b} (OSM shared node{'s' if len(els) > 1 else ''}: {len(els)})",
               "n_matches": len(els), "method": "OSM street intersection (approximate site location)"}
    cache[key] = res
    return res


def nominatim(addr):
    key = "NOMINATIM:" + addr
    if key in cache:
        return cache[key]
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": addr, "format": "json", "limit": 1,
                     "countrycodes": "us"}, headers={"User-Agent": "CA17-research-script/1.0 (academic GIS project)"}, timeout=60)
    js = r.json()
    res = None
    if js:
        res = {"lon": float(js[0]["lon"]), "lat": float(js[0]["lat"]), "matched": js[0]["display_name"][:120],
               "n_matches": 1, "method": f"OSM Nominatim ({js[0].get('class')}/{js[0].get('type')})"}
    cache[key] = res
    time.sleep(1.1)  # Nominatim usage policy: <=1 request/second
    return res


# ZIP codes used only for fallback geocoding (from USPS/City records of the listed street addresses)
ZIP_FALLBACK = {"SJ03": "5601 Great Oaks Parkway, San Jose, CA 95119", "SJ10": "2549 Orchard Parkway, San Jose, CA 95134",
                "SJ14": "1657 Alviso-Milpitas Road, San Jose, CA 95002", "CEC01": "2805 Bowers Avenue, Santa Clara, CA 95051",
                "CEC02": "2825 Lafayette Street, Santa Clara, CA 95050"}

inv = pd.read_csv(INV / "facility_inventory_sources.csv", dtype=str)
log("Inventory records:", len(inv), inv.facility_type.value_counts().to_dict())
geo = []
for _, r in inv.iterrows():
    if r.geocode_address.startswith("INTERSECTION"):
        g = osm_intersection("West Trimble Road", "Orchard Parkway")
    else:
        g = census_geocode(r.geocode_address)
        if g is None and r.inv_id in ZIP_FALLBACK:
            g = census_geocode(ZIP_FALLBACK[r.inv_id]) or nominatim(ZIP_FALLBACK[r.inv_id]) \
                or nominatim(ZIP_FALLBACK[r.inv_id].replace(" Parkway", " Pkwy").rsplit(" ", 1)[0])
    geo.append(g or {"lon": np.nan, "lat": np.nan, "matched": "NO MATCH", "n_matches": 0, "method": "unmatched"})
cache_f.write_text(json.dumps(cache, indent=1))
g = pd.DataFrame(geo)
inv = pd.concat([inv, g.rename(columns={"matched": "geocode_matched", "method": "geocode_method",
                                        "n_matches": "geocode_n"})], axis=1)
inv["accessed"] = "2026-11-10"
for c in ["building_sqft", "power_mw"]:
    inv[c] = pd.to_numeric(inv[c], errors="coerce")
unm = inv[inv.lon.isna()]
log("Geocode results:\n" + inv[["inv_id", "geocode_address", "geocode_matched", "geocode_method"]].to_string())
log("UNMATCHED:", list(unm.inv_id))

fac = gpd.GeoDataFrame(inv, geometry=gpd.points_from_xy(inv.lon, inv.lat), crs="EPSG:4326").to_crs(CRS)
fac_unmatched = fac[fac.lon.isna()].drop(columns="geometry")

# ------------------------------------------------------------------ OSM existing data centers
raw = json.loads((ROOT / "data/external/osm/overpass_datacenters_raw.json").read_text())
log("\nOSM base timestamp:", raw["osm3s"]["timestamp_osm_base"], " elements:", len(raw["elements"]))
rows = []
for e in raw["elements"]:
    t = e.get("tags", {})
    c = e.get("center", e)
    rows.append({"osm_type": e["type"], "osm_id": e["id"], "name": t.get("name"), "operator": t.get("operator"),
                 "street": t.get("addr:street"), "housenumber": t.get("addr:housenumber"), "city": t.get("addr:city"),
                 "telecom": t.get("telecom"), "building": t.get("building"), "lat": c["lat"], "lon": c["lon"]})
osm = pd.DataFrame(rows)
osm = gpd.GeoDataFrame(osm, geometry=gpd.points_from_xy(osm.lon, osm.lat), crs="EPSG:4326").to_crs(CRS)
# De-duplicate features that represent the same facility: same name+operator within 150 m
osm["dup_of"] = None
for i, a in osm.iterrows():
    if osm.at[i, "dup_of"] is not None or not a["name"]:
        continue
    same = osm[(osm.index > i) & (osm.name == a["name"]) & (osm.geometry.distance(a.geometry) < 150)]
    osm.loc[same.index, "dup_of"] = f"{a.osm_type}/{a.osm_id}"
log("OSM features flagged as duplicates (same name, <150 m):", int(osm.dup_of.notna().sum()))

# ------------------------------------------------------------------ spatial context
cd = gpd.read_file(GPKG, layer="ca17_district_120th")
reg = gpd.read_file(GPKG, layer="region_tracts_3county")
cty = gpd.read_file(GPKG, layer="region_counties")
cdg = cd.geometry.iloc[0]
TRACT_COLS = ["GEOID_std", "county_name", "ces_CIscoreP", "ces_PollutionP", "ces_PopCharP", "ces_dieselP",
              "pct_burden30", "pct_burden30_moe", "rent_hh_computed", "mhi", "burden_t", "ces_t", "bivar",
              "ces_ACS2024Pop"]


def add_context(pts, label):
    pts = pts.copy()
    pts["in_ca17"] = pts.within(cdg).astype(int)
    pts["dist_ca17_m"] = pts.distance(cdg).round(0)
    j = gpd.sjoin(pts, reg[TRACT_COLS + ["geometry"]], how="left", predicate="within").drop(columns="index_right")
    j = j.rename(columns={"GEOID_std": "host_tract", "county_name": "host_county"})
    # Approximate resident population within 1 km: tract population x share of tract area inside buffer.
    # Assumes uniform population within tracts — a coarse screening estimate, not a count.
    reg_a = reg[["GEOID_std", "ces_ACS2024Pop", "geometry"]].copy()
    reg_a["tarea"] = reg_a.area
    pops = []
    for geom in j.geometry:
        if geom is None or geom.is_empty:
            pops.append(np.nan)
            continue
        buf = geom.buffer(1000)
        cand = reg_a[reg_a.intersects(buf)]
        share = cand.intersection(buf).area / cand.tarea
        pops.append(float((share * cand.ces_ACS2024Pop.fillna(0)).sum()))
    j["pop_1km_est"] = np.round(pops, -2)
    log(f"\n{label}: {len(j)} points | in CA-17: {int(j.in_ca17.sum())} | outside 3-county frame: {int(j.host_tract.isna().sum())}")
    return j


fac = add_context(fac[fac.lon.notna()], "Documented inventory")
if len(fac_unmatched):
    log("NOT MAPPED (no geocode):", list(fac_unmatched.inv_id))
osm_c = add_context(osm, "OSM existing")
osm_u = osm_c[osm_c.dup_of.isna()]
log("OSM unique facilities in 3-county frame:", int(osm_u.host_tract.notna().sum()), "| in CA-17:", int(osm_u.in_ca17.sum()))
log("OSM unique by county:", osm_u.host_county.value_counts(dropna=False).to_dict())

# Summary of documented inventory
cols = ["inv_id", "facility_name", "facility_type", "source_id", "city", "status_class", "power_mw", "building_sqft",
        "in_ca17", "dist_ca17_m", "host_county", "host_tract", "ces_CIscoreP", "pct_burden30", "bivar", "pop_1km_est"]
log("\n" + fac[cols].sort_values(["facility_type", "in_ca17"], ascending=[True, False]).to_string())

# Tract-level counts of existing (OSM) data centers
cnt = osm_u.groupby("host_tract").size().rename("osm_dc_n")
reg = reg.drop(columns=[c for c in ("osm_dc_n", "hosts_dc") if c in reg]).merge(cnt, left_on="GEOID_std", right_index=True, how="left")
reg["osm_dc_n"] = reg.osm_dc_n.fillna(0).astype(int)

# Comparison: CES and burden in tracts hosting >=1 existing OSM data center vs other tracts (3-county frame)
reg["hosts_dc"] = (reg.osm_dc_n > 0).astype(int)
comp = reg.groupby("hosts_dc").agg(n=("GEOID_std", "size"), ces_median=("ces_CIscoreP", "median"),
                                   poll_median=("ces_PollutionP", "median"), popchar_median=("ces_PopCharP", "median"),
                                   burden_median=("pct_burden30", "median"), pop_sum=("ces_ACS2024Pop", "sum"))
log("\nExisting-DC host tracts vs other tracts (3 counties):\n" + comp.to_string())
comp.to_csv(OUT / "dc_host_tract_comparison.csv")

# ------------------------------------------------------------------ write
fac.to_file(GPKG, layer="facilities_documented", driver="GPKG")
osm_c.to_file(GPKG, layer="datacenters_osm_existing", driver="GPKG")
reg.to_file(GPKG, layer="region_tracts_3county", driver="GPKG")
pd.concat([fac.drop(columns="geometry"), fac_unmatched]).to_csv(OUT / "facilities_documented.csv", index=False)
osm_c.drop(columns="geometry").to_csv(OUT / "datacenters_osm_existing.csv", index=False)
log("\nWrote facility layers.")
LOG.close()
