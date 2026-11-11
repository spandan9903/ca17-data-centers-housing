"""
07_build_appendix.py — Data & Methodology Appendix (docs/CA17_Methods_Appendix.pdf), generated from processed tables.
"""
import json
from pathlib import Path

import pandas as pd
import geopandas as gpd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
S = json.load(open(P / "summary_stats.json"))
OUT = ROOT / "docs/CA17_Methods_Appendix.pdf"
F = "/System/Library/Fonts/Supplemental/"
for n, f in [("Ar", "Arial.ttf"), ("ArB", "Arial Bold.ttf"), ("ArI", "Arial Italic.ttf")]:
    pdfmetrics.registerFont(TTFont(n, F + f))
pdfmetrics.registerFont(TTFont("ArU", F + "Arial Unicode.ttf"))
registerFontFamily("Ar", normal="Ar", bold="ArB", italic="ArI", boldItalic="ArB")
NAVY = colors.HexColor("#1f3a5f")
st = {"h1": ParagraphStyle("h1", fontName="ArB", fontSize=16, leading=20, textColor=NAVY, spaceAfter=4),
      "h2": ParagraphStyle("h2", fontName="ArB", fontSize=11, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=3, keepWithNext=1),
      "b": ParagraphStyle("b", fontName="Ar", fontSize=8.6, leading=11.2, spaceAfter=4),
      "bul": ParagraphStyle("bul", fontName="Ar", fontSize=8.6, leading=11.2, leftIndent=10, spaceAfter=2.5),
      "c": ParagraphStyle("c", fontName="Ar", fontSize=6.9, leading=8.4),
      "ch": ParagraphStyle("ch", fontName="ArB", fontSize=6.9, leading=8.4, textColor=colors.white),
      "code": ParagraphStyle("code", fontName="Courier", fontSize=7.6, leading=9.4, leftIndent=8, spaceAfter=4,
                             backColor=colors.HexColor("#f4f6f9"))}
U = lambda t: t.replace("≥", '<font name="ArU">≥</font>').replace("±", '<font name="ArU">±</font>').replace("≤", '<font name="ArU">≤</font>').replace("×", '<font name="ArU">×</font>').replace("√", '<font name="ArU">√</font>')
p = lambda t, s="b": Paragraph(U(t), st[s])
bl = lambda items: [Paragraph(U(x), st["bul"], bulletText="•") for x in items]


def table(rows, widths, header=True):
    rr = [[Paragraph(U(str(v)), st["ch"] if (header and i == 0) else st["c"]) for v in r] for i, r in enumerate(rows)]
    t = Table(rr, colWidths=[w * inch for w in widths], repeatRows=1 if header else 0)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY if header else colors.white),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8ced8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8)]))
    return t


def footer(c, d):
    c.saveState(); c.setFont("Ar", 7); c.setFillColor(colors.grey)
    c.drawString(0.6 * inch, 0.4 * inch, "CA-17 Technology Growth & Community Costs — Data and Methodology Appendix (November 2026)")
    c.drawRightString(letter[0] - 0.6 * inch, 0.4 * inch, f"A-{d.page}"); c.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.55 * inch,
                        bottomMargin=0.6 * inch, title="CA-17 Data and Methodology Appendix")
E = [p("Data and Methodology Appendix", "h1"),
     p("Technology Growth and Community Costs in Silicon Valley — California’s 17th Congressional District (120th Congress boundaries, effective 3 January 2027). "
       "This appendix documents every dataset, processing decision, join, calculation and limitation behind the briefing. All numbers are produced by the scripts "
       "in <font name='Courier'>scripts/</font>; logs are in <font name='Courier'>logs/</font>.")]

# ---------------------------------------------------------------- A1 inventory
E += [p("A1. Dataset inventory and audit", "h2")]
inv = [["Dataset (file)", "Source / vintage", "Geography & records", "Identifier", "Status in analysis"],
       ["CA17_Study_Area.gpkg", "Census 2026 TIGER/Line, 120th Congress CDs (layer tl_2026_06_cd120shp)", "1 polygon, EPSG:4269", "GEOID 0617", "Used — study area"],
       ["CA17_Census_Tracts.gpkg", "Census 2026 TIGER/Line tracts (2020 tract vintage) selected with Intersects", "202 polygons (Santa Clara 169, Alameda 32, San Mateo 1)", "GEOID (11 char)", "Used — overlap-classified (A3)"],
       ["Median Household Income.zip", "ACS 2020–2024 5-yr B19013 (data.census.gov)", "88,605 rows, all U.S. summary levels → 9,129 CA tracts", "GEO_ID 1400000US + 11", "Used"],
       ["Median Gross Rent.zip", "ACS 2020–2024 5-yr B25064", "same", "GEO_ID", "Used"],
       ["Gross Rent as % of HH Income.zip", "ACS 2020–2024 5-yr B25070 (001–011)", "same", "GEO_ID", "Used"],
       ["GrossRentas%ofincome.gpkg", "Attribute-only copy of B25070 CSV (9,129 rows, no geometry)", "—", "GEO_ID", "Not used (duplicate of zip)"],
       ["calenviroscreen50results_f_070126.shp.zip", "OEHHA CalEnviroScreen 5.0 final results (metadata 8 Jun 2026)", "9,106 tracts, EPSG:3310; −999 = no data", "tract (float, no leading 0)", "Used"],
       ["CaliforniaEA_ada.csv", "CEC Energy Equity Indicators (energy affordability) — page states “Data is NOT final”; updated 15 Sep 2025", "27,022 rows = 9,040 tracts × tenant type (COM 9,040 / REN 9,029 / OWN 8,953)", "FIP (10 digits, no leading 0)", "Joined; context only (draft)"],
       ["Alameda Housing Data.xlsx; SC Housing Data.xlsx", "HCD Housing Element Sites Inventory extract (land_use_last_update 2022-11-21)", "17 parcels, all jurisdiction = City of Alameda", "parcel_id / APN", "Not used: files are byte-identical (MD5 e18ec5bf…) and cover the City of Alameda, outside CA-17"],
       ["Ro Khanna Project.qgz", "User’s earlier QGIS project", "references local TIGER zips + VersaTiles basemap", "—", "Inspected only"],
       ["BAAQMD Permitted & Proposed Data Centers (Phase 1) FeatureServer; AGOL item 7d1bb8b5…", "Bay Area Air District", "—", "—", "NOT accessible: service HTTP 499 ‘Token Required’; item, /data and search return 403 / not indexed (anonymous). Not bypassed."],
       ["City of San José — Data Center and other Large Energy-Use Projects", "sanjoseca.gov, page updated 11/04/2026; read 10 Nov 2026 in a browser (site blocks scripted fetches)", "14 data-center + 2 large-energy records", "SJPermits file #", "Used — transcribed"],
       ["CEC Power Plant Listing / SPPE dockets", "energy.ca.gov, read 10 Nov 2026", "Bay Area data-center backup-generation dockets", "Docket #", "Used — 6 records not on the San José list; 3 cross-referenced"],
       ["OpenStreetMap via Overpass API", "telecom=data_center or building=data_center, bbox 36.9–37.95N, 122.6–121.4W; OSM base 2026-11-11T01:12Z", "85 features (5 flagged duplicates)", "osm type/id", "Used — existing facilities (context)"],
       ["PNNL IM3 Open Source Data Center Atlas v2026.11.02", "MSD-LIVE, doi:10.57931/2550666 (OSM-derived)", "GPKG/CSV", "id", "Not downloaded: download requires MSD-LIVE CLI login / browser-issued credentials; same OSM source queried directly instead"],
       ["Esri World Light Gray Canvas", "server.arcgisonline.com tiles cached to GeoTIFF (≈9.55 m/px)", "basemap", "—", "Used — cartography only"]]
E += [table(inv, [1.55, 1.75, 1.45, 0.9, 1.65])]

# ---------------------------------------------------------------- A2 geography
d = S["district_set"]
cc = pd.read_csv(P / "ca17_county_composition.csv")
E += [p("A2. Geographic processing", "h2")] + bl([
    "All area calculations in EPSG:3310 (California Albers, NAD83, equal-area). Geometries validated (0 invalid) and passed through make_valid.",
    "Overlap share = area(tract ∩ CA-17) / area(tract). Sum of intersections equals the district area (490.73 km²), confirming complete tract coverage.",
    f"Classes: within ≥90% ({S['overlap_classes']['1_within (>=90%)']}), majority 50–90% ({S['overlap_classes']['2_majority (50-90%)']}), "
    f"minority 5–50% ({S['overlap_classes']['3_minority (5-50%)']}), sliver &lt;5% ({S['overlap_classes']['4_sliver (<5%)']}).",
    f"<b>Analytical rule:</b> the district analysis set is the {d['n_tracts']} tracts with ≥50% of area in CA-17 (Santa Clara {d['by_county_tracts'].get('085')}, "
    f"Alameda {d['by_county_tracts'].get('001')}). Their 2024 ACS population (via CES 5.0 ACS2024Pop) is {d['pop_ces2024']:,.0f}, close to the ≈760,350 equal-population "
    "target (2020 Census California population 39,538,223 ÷ 52 seats), so the rule reproduces the district population well. Minority and sliver tracts are retained in every "
    "layer (flag in_district_set = 0) and appear in regional analysis; nothing is dropped. Area weighting of counts was rejected because it assumes uniform population.",
    "County composition (overlay of CA-17 with county polygons dissolved from CES 5.0 tracts): " + "; ".join(f"{r.county} {r.share*100:.1f}% ({r.area_km2:.0f} km²)" for r in cc.itertuples())
    + ". No San Mateo County area; the single San Mateo tract (06081990100, water) is a boundary sliver. This matches the published Proposition 50 description of CA-17 "
    "(parts of Alameda and Santa Clara counties: Newark, part of Fremont; Cupertino, Milpitas, Santa Clara, Sunnyvale and part of San José).",
    "Regional frame: all 959 CES 5.0 tracts in Alameda, Santa Clara and San Mateo counties (2020 tract geometry, identical GEOIDs to TIGER 2020 tracts).",
    "Maps use Web Mercator (EPSG:3857) to match the basemap; scale bars are measured on the WGS84 ellipsoid. District maps clip tract polygons to the CA-17 boundary for display only.",
])

# ---------------------------------------------------------------- A3 variables & calculations
E += [p("A3. Variables and calculations", "h2")]
E += [table([["Field", "Definition / formula"],
             ["GEOID_std", "11-character tract FIPS. ACS: last 11 characters of GEO_ID (prefix 1400000US). CES: int(tract) zero-padded to 11. CEC: FIP zero-padded. Original fields kept."],
             ["mhi, mhi_moe", "B19013_001E/M, median household income (2024 dollars). ‘250,000+’ → 250000 with mhi_flag = top-coded."],
             ["mgr, mgr_moe", "B25064_001E/M, median gross rent. ‘3,500+’ → 3500, top-coded flag. ‘-’ → missing (suppressed / no renters)."],
             ["rent_hh_computed", "B25070_001 − B25070_011 (renter households for whom the rent-to-income ratio is computed). MOE = √(M001² + M011²)."],
             ["pct_burden30", "100 × (B25070_007 + 008 + 009 + 010) / rent_hh_computed. Numerator MOE = √ΣM². Proportion MOE: Census ACS Handbook (2020) formula √(MOEnum² − p²·MOEden²)/den, ratio formula if radicand &lt; 0."],
             ["pct_burden50", "100 × B25070_010 / rent_hh_computed (same MOE method)."],
             ["*_cv, *_rel", "CV = (MOE/1.645)/estimate × 100. Reliability: high ≤15, medium ≤30, fair ≤40, low &gt;40. Maps hatch burden with CV &gt;40 or &lt;50 renter HH."],
             ["District pooled shares", "Σ tract numerators / Σ tract denominators over the analysis set; MOEs via √ΣM² and the proportion formula. Medians are not pooled; the distribution of tract medians is reported."],
             ["ces_* fields", "CES 5.0 overall score/percentile (CIscore/P), Pollution Burden (Pollution/S/P), Population Characteristics (PopChar/Sco/P) and indicator percentiles (statewide). −999 set to missing."],
             ["burden_t, ces_t, bivar", "Terciles across the 959 regional tracts (burden only where rent_hh_computed ≥50). Cut points: burden 41.1% / 55.1%; CES 21.3 / 46.0 percentile. bivar = ‘burden_t-ces_t’."],
             ["screen_overlap", "1 if burden_t = 3 AND ces_t = 3 (no weighting, no index)."],
             ["pop_1km_est", "Σ tract population × share of tract area within 1 km of a facility. Screening approximation (uniform-population assumption)."],
             ["osm_dc_n", "Count of de-duplicated OSM data-center features within the tract (duplicates: same name within 150 m)."]],
            [1.3, 6.0])]

# ---------------------------------------------------------------- A4 join validation
jv = pd.read_csv(P / "join_validation.csv").fillna("")
mv = pd.read_csv(P / "missing_values_ca17.csv", index_col=0)
E += [p("A4. Join validation and missing values", "h2"),
      table([["Join", "Records", "Matched", "Unmatched", "Unmatched IDs"]] + jv.values.tolist(), [2.3, 0.7, 0.7, 0.75, 2.85])]
E += bl(["06001990000 and 06081990100 are water-only tracts (0 population); CES 5.0 omits them. 06001444303 (within CA-17) has no households in ACS and no CEC record.",
         "Missing values (all 202 / district set): " + "; ".join(f"{i} {r.all_202}/{r.district_set}" for i, r in mv.iterrows()) + ".",
         f"Top-coding in the district set: {S['mhi_topcoded_n']} tracts at $250,000+ income and {S['mgr_topcoded_n']} at $3,500+ rent (listed in data/processed/acs_flags_ca17.csv).",
         f"{S['burden30_cv_gt40_n']} district tracts have burden CV &gt;40% (low reliability); 2 have &lt;50 renter households and are left unclassified in the screen."])

# ---------------------------------------------------------------- A5 CES
ci = pd.read_csv(P / "table_ces_indicators_district.csv")
E += [p("A5. CalEnviroScreen 5.0 — what it measures, and district results", "h2"),
      p("CalEnviroScreen (OEHHA, for CalEPA) ranks census tracts by cumulative burden: Pollution Burden (exposure indicators such as ozone, PM2.5, diesel PM, "
        "traffic, toxic releases, drinking-water contaminants, lead risk, pesticides; and environmental-effects indicators such as cleanup sites, groundwater threats, "
        "hazardous-waste facilities, impaired waters, solid-waste sites) × Population Characteristics (asthma, low birth weight, cardiovascular disease; education, "
        "linguistic isolation, poverty, unemployment, housing burden). Scores are relative statewide percentiles. It does not measure facility-specific emissions, noise, "
        "heat, water withdrawals or electricity demand, and indicator data lag the release by one to several years. A high score therefore cannot be attributed to any "
        "individual facility."),
      table([["Indicator (statewide pct.)", "Median tract", "Pop-weighted mean", "% tracts ≥75th"]] +
            [[r.indicator, f"{r.median_tract_pctile:.1f}", f"{r.pop_weighted_mean_pctile:.1f}", f"{r.share_tracts_ge75:.1f}"] for r in ci.itertuples()],
            [2.0, 1.0, 1.2, 1.1])]

# ---------------------------------------------------------------- A6 facilities
fac = pd.read_csv(P / "facilities_documented.csv")
E += [PageBreak(), p("A6. Documented facility inventory (verified sources)", "h2"),
      p("Each record is transcribed from an official web page (URL in data/external/inventory/facility_inventory_sources.csv), retains its permit or docket ID, and "
        "is geocoded with the U.S. Census Geocoder; five addresses not matched by Census were geocoded with OSM Nominatim (house-level except SJ14, street-level) and "
        "NorthTown (CEC04) is placed at the W Trimble Rd / Orchard Pkwy intersection named in its docket. Data centers and the City’s ‘large energy-use (not data "
        "center)’ projects are kept separate. Out-of-region CEC dockets (RB Inyokern, Kern Co.; Vernon, Los Angeles Co.) were excluded; Pittsburg (Contra Costa) is kept but "
        "lies outside the map frame. ‘Approved / exempted’ means a planning approval or CEC exemption, not construction or operation."),
      table([["ID", "Project", "Type", "Source ID", "Status", "Submitted / approved", "MW (basis)", "Sq ft", "In CA-17", "Geocode"]] +
            [[r.inv_id, r.facility_name, "DC" if r.facility_type == "data_center" else "LEU (not DC)", r.source_id, r.status_class,
              f"{'' if pd.isna(r.submitted_date) else r.submitted_date} / {'' if pd.isna(r.approved_date) else r.approved_date}",
              "—" if pd.isna(r.power_mw) else f"{r.power_mw:g} ({str(r.power_basis).split(':')[0]})",
              "—" if pd.isna(r.building_sqft) else f"{r.building_sqft:,.0f}", "Yes" if r.in_ca17 == 1 else f"No ({r.dist_ca17_m/1000:.1f} km)",
              str(r.geocode_method).split(" (")[0]] for r in fac.itertuples()],
            [0.45, 1.5, 0.42, 0.8, 0.72, 0.82, 0.68, 0.52, 0.58, 0.63])]
E += bl(["Cross-references: SJ02 = CEC 26-SPPE-03 (Charcot Ave); SJ05 = CEC 26-SPPE-02 (Silver Creek); SJ14 = CEC 19-SPPE-04 (Microsoft, 1657 Alviso-Milpitas Rd); "
         "SJ10 ≈ CEC 22-SPPE-02 (Microsoft SJDC 04; matched on site and building program). CEC04 NorthTown may relate to SJ08 (CP23-013) but acreage and generator "
         "counts differ, so both are retained.",
         "OpenStreetMap existing facilities: 85 features retrieved, 5 duplicates flagged (not deleted), 76 unique within the three-county frame, 63 inside CA-17. OSM is "
         "crowd-sourced; presence/absence is not verified and the layer must not be read as a census of facilities.",
         "The Bay Area Air District inventory could not be retrieved. If the Air District makes it public, scripts/02_facilities.py can ingest it as an additional layer, "
         "and maps re-export with scripts/05_build_qgis_project.py."])

# ---------------------------------------------------------------- A7 limitations
E += [p("A7. Limitations", "h2")] + bl([
    "Partial facility inventory (San José + CEC dockets + OSM). Cities of Santa Clara, Milpitas, Sunnyvale and Fremont publish no comparable list; projects below CEC thresholds outside San José are missing.",
    "ACS: 5-year pooled estimates (2020–2024); large tract MOEs; top-coding at $250,000 / $3,500 understates the upper tail; tract medians cannot be aggregated.",
    "Tract assignment by area share, not population; some residents of majority tracts live outside CA-17 and vice versa. Large, sparsely populated tracts (e.g., 5046.02 Alviso/baylands, 64 km², ≈1,500 residents) dominate visually.",
    "CalEnviroScreen is a relative screening tool; indicator vintages vary and pre-date recent projects. It does not capture backup-generator emissions specifically.",
    "Bivariate terciles are relative to the three-county region; different breaks would move tracts between classes. No composite index is constructed.",
    "MW figures mix bases (backup-generation capacity, maximum load, equipment capacity) and are not additive or indicative of actual consumption. CEC SPPE dockets cover 50–100 MW backup plants by definition, so the 90–99.8 MW clustering is partly a selection effect.",
    "CEC energy-affordability data are draft and were used only for a contextual statement (renter energy burden median ≈1.0% of income in district tracts; none above 6%).",
    "Correlation (Spearman rho = %.2f between burden and CES across district tracts) and proximity are descriptive; no causal claim is made about data centers and housing costs or environmental scores." % S["spearman_burden_ces"]["rho"],
    "District boundary is the incoming 120th-Congress geography (effective 3 Jan 2027), not the 119th-Congress district currently in effect.",
])

# ---------------------------------------------------------------- A8 reproducibility
E += [p("A8. Reproducibility", "h2"),
      p("Environment: QGIS 3.44 bundled Python 3.12 (PyQGIS, GeoPandas, pyogrio, SciPy); openpyxl, ReportLab and pypdf installed to scripts/_pylib. Run from the project root:"),
      Paragraph("source scripts/env.sh<br/>"
                "$QGIS_APP/MacOS/python scripts/01_prepare_data.py&nbsp;&nbsp;&nbsp;# geography, ACS, CES, CEC joins<br/>"
                "$QGIS_APP/MacOS/python scripts/02_facilities.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# geocode inventory, OSM, proximity<br/>"
                "$QGIS_APP/MacOS/python scripts/03_summary_stats.py&nbsp;&nbsp;# statistics -> summary_stats.json<br/>"
                "bash scripts/04_cache_basemap.sh; $QGIS_APP/MacOS/python scripts/04b_city_labels.py<br/>"
                "$QGIS_APP/MacOS/python scripts/05_build_qgis_project.py # QGIS project + 3 layouts + exports<br/>"
                "$QGIS_APP/MacOS/python scripts/06_build_briefing.py; $QGIS_APP/MacOS/python scripts/07_build_appendix.py", st["code"]),
      p("Raw inputs in data/raw are read-only copies of the supplied files; external downloads (OSM JSON, geocode cache, transcribed inventory) are in data/external. "
        "The Overpass query and geocoder responses are cached so reruns are deterministic; delete the caches to refresh.")]

# ---------------------------------------------------------------- A9 citations
E += [p("A9. Source citations (all accessed 10 November 2026 unless noted)", "h2")] + bl([
    "U.S. Census Bureau. American Community Survey 2020–2024 5-Year Estimates, Tables B19013, B25064, B25070. data.census.gov.",
    "U.S. Census Bureau. 2026 TIGER/Line Shapefiles: Congressional Districts (120th Congress) and Census Tracts, California.",
    "U.S. Census Bureau (2020). Understanding and Using ACS Data: What All Data Users Need to Know (ACS Handbook) — MOE formulas.",
    "California Office of Environmental Health Hazard Assessment. CalEnviroScreen 5.0 results shapefile (CES5_final_shapefile, June 2026). oehha.ca.gov/calenviroscreen.",
    "City of San José, Planning, Building & Code Enforcement. “Data Center and other Large Energy-Use Projects” (updated 11/04/2026). sanjoseca.gov.",
    "California Energy Commission. Power Plant Listing; docket pages 19-SPPE-04, 20-SPPE-02, 22-SPPE-01, 22-SPPE-02, 22-SPPE-03, 23-SPPE-01, 24-SPPE-01, 25-SPPE-02, 26-SPPE-02, 26-SPPE-03. energy.ca.gov/proceedings/power-plant-listing. Lafayette address from CEC Draft EIR / CEQAnet SCH 2021080074.",
    "California Energy Commission. Energy Equity Indicators — Deep Dive: Energy (draft; data updated 15 Sep 2025). energy.ca.gov.",
    "Bay Area Air District. Data Centers and the Air District (baaqmd.gov/Rules-and-Compliance/Data-Centers); “Permitted and Proposed Data Centers Phase 1” FeatureServer (not publicly accessible).",
    "Mongird, K., Thurber, T., Vernon, C., Burleyson, C., Akdemir, K.Z., Rice, J. IM3 Open Source Data Center Atlas. PNNL / MSD-LIVE. doi:10.57931/2550666 (v2026.11.02).",
    "OpenStreetMap contributors (ODbL 1.0), via Overpass API (overpass-api.de) and Nominatim.",
    "California Senate Office of Demographics; California Secretary of State — Proposition 50 (2025) congressional map materials (county composition cross-check).",
    "Esri. World Light Gray Canvas Base and Reference (Esri, HERE, Garmin, © OpenStreetMap contributors).",
])
doc.build(E, onFirstPage=footer, onLaterPages=footer)
print("Wrote", OUT)
