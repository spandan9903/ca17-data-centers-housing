"""Fetch city label points (place nodes) from OSM Nominatim for map reference labels -> data/external/osm/city_labels.csv"""
import csv, time, requests
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "data/external/osm/city_labels.csv"
CITIES = ["Fremont", "Newark", "Milpitas", "City of Santa Clara", "Sunnyvale", "Cupertino", "San Jose", "Mountain View",
          "Campbell", "Saratoga", "Los Gatos", "Palo Alto", "Union City", "Alviso, San Jose", "Los Altos"]
rows = []
for c in CITIES:
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": f"{c}, California", "format": "json", "limit": 1},
                     headers={"User-Agent": "CA17-research-script/1.0 (academic GIS project)"}, timeout=60).json()
    if r:
        rows.append({"name": c.split(",")[0].replace("San Jose", "San José").replace("City of ", ""), "lat": r[0]["lat"], "lon": r[0]["lon"], "osm": f"{r[0]['osm_type']}/{r[0]['osm_id']}"})
    time.sleep(1.1)
# Nominatim's "City of Santa Clara" hit is a non-centroid node; use Santa Clara City Hall (Census Geocoder) instead.
g = requests.get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                 params={"address": "1500 Warburton Ave, Santa Clara, CA", "benchmark": "Public_AR_Current", "format": "json"}, timeout=60).json()
c = g["result"]["addressMatches"][0]["coordinates"]
rows = [r for r in rows if r["name"] != "Santa Clara"] + [{"name": "Santa Clara", "lat": c["y"], "lon": c["x"], "osm": "Census Geocoder: City Hall, 1500 Warburton Ave"}]
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "lat", "lon", "osm"]); w.writeheader(); w.writerows(rows)
print(rows)
