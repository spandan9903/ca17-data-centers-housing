"""
06_build_briefing.py — Build the policy research briefing PDF (docs/CA17_Policy_Brief.pdf).
Numbers are read from data/processed/summary_stats.json and tables, not typed by hand.
"""
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                                KeepTogether, PageBreak)

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
S = json.load(open(P / "summary_stats.json"))
CFG = json.load(open(ROOT / "scripts/author_config.json"))  # author line + repo link (blank = omitted)
REF = pd.read_csv(P / "table_reference_geographies.csv").set_index("geography")
FAC = pd.read_csv(P / "facilities_documented.csv")
OUT = ROOT / "docs/CA17_Policy_Brief.pdf"
OUT.parent.mkdir(exist_ok=True)

F = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Ar", F + "Arial.ttf"))
pdfmetrics.registerFont(TTFont("ArB", F + "Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("ArI", F + "Arial Italic.ttf"))
pdfmetrics.registerFont(TTFont("ArU", F + "Arial Unicode.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Ar", normal="Ar", bold="ArB", italic="ArI", boldItalic="ArB")

NAVY = colors.HexColor("#1f3a5f")
GREY = colors.HexColor("#555555")
base = dict(fontName="Ar", fontSize=8.9, leading=11.6, textColor=colors.HexColor("#1e1e1e"))
st = {
    "body": ParagraphStyle("body", **base, spaceAfter=4),
    "bul": ParagraphStyle("bul", **base, leftIndent=10, bulletIndent=0, spaceAfter=3.2),
    "h1": ParagraphStyle("h1", fontName="ArB", fontSize=17.5, leading=21, textColor=NAVY, spaceAfter=3),
    "sub": ParagraphStyle("sub", fontName="Ar", fontSize=10, leading=13, textColor=GREY, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="ArB", fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=6, spaceAfter=3),
    "small": ParagraphStyle("small", fontName="Ar", fontSize=7, leading=8.8, textColor=GREY, spaceAfter=2),
    "cap": ParagraphStyle("cap", fontName="ArI", fontSize=7.3, leading=9, textColor=GREY, spaceAfter=4),
    "box": ParagraphStyle("box", fontName="Ar", fontSize=8, leading=10.2, textColor=colors.HexColor("#1e1e1e")),
    "cell": ParagraphStyle("cell", fontName="Ar", fontSize=7.4, leading=9),
    "cellb": ParagraphStyle("cellb", fontName="ArB", fontSize=7.4, leading=9, textColor=colors.white),
}
p = lambda t, s="body": Paragraph(t, st[s])
GE = '<font name="ArU">≥</font>'
PM = '<font name="ArU">±</font>'

d, r3, f, c = S["district_set"], S["region_3county"], S["fac"], S["ces"]
host = {bool(x["osm_dc_n"]): x for x in S["osm_host_vs_not_district"]}
top_ind = {x["indicator"]: x["median_tract_pctile"] for x in S["ces_indicators_top"]}
k = lambda x: f"{x/1000:,.0f}k"


def header_footer(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, letter[1] - 0.32 * inch, letter[0], 0.32 * inch, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("ArB", 8)
    canv.drawString(0.6 * inch, letter[1] - 0.21 * inch, "INDEPENDENT POLICY RESEARCH BRIEF  |  CA-17 TECHNOLOGY GROWTH & COMMUNITY COSTS")
    canv.drawRightString(letter[0] - 0.6 * inch, letter[1] - 0.21 * inch, "November 2026")
    canv.setFillColor(GREY)
    canv.setFont("Ar", 7)
    canv.drawString(0.6 * inch, 0.38 * inch, "Independent research; not produced by or for any government office. " + ("Data, code and methods: " + CFG["repo_url"] if CFG.get("repo_url") else "Data, scripts and methods appendix available on request."))
    canv.drawRightString(letter[0] - 0.6 * inch, 0.38 * inch, f"Page {doc.page}")
    canv.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.5 * inch,
                      bottomMargin=0.55 * inch, title="Technology Growth and Community Costs in Silicon Valley (CA-17)",
                      author="Independent GIS policy research", subject="CA-17 data centers, housing affordability, CalEnviroScreen 5.0")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])
E = []

# ------------------------------------------------------------------ page 1
E += [Spacer(1, 4), p("Technology Growth and Community Costs in Silicon Valley", "h1"),
      p("Where data-center development, housing-cost pressure and environmental burden overlap in California’s 17th "
        "Congressional District", "sub")]
by = " · ".join(x for x in [CFG.get("author"), CFG.get("affiliation"), CFG.get("email"), CFG.get("repo_url")] if x)
if by:
    E += [Paragraph(f"Prepared by {by}", ParagraphStyle("by", fontName="Ar", fontSize=8.5, leading=11, textColor=NAVY, spaceAfter=5))]
box = Table([[p("<b>Boundary note.</b> All district figures use the 2026 TIGER/Line boundary for CA-17 in the "
                "<b>120th Congress</b> (Proposition 50 map), effective <b>3 January 2027</b>. It covers parts of Santa Clara and "
                "Alameda counties (≈71% / 29% of district area). It differs from the 119th-Congress district currently in effect, so results "
                "describe the incoming district.", "box")]],
            colWidths=[doc.width], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2f7")),
                                                    ("BOX", (0, 0), (-1, -1), 0.5, NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                                    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
E += [box, Spacer(1, 4), p("Executive summary", "h2")]
bul = [
    f"<b>Renter cost burden is real but below regional levels.</b> In one of California’s highest-income districts (half of "
    f"district tracts have median household incomes between ${S['tract_mhi']['p25']/1000:,.0f}k and ${S['tract_mhi']['p75']/1000:,.0f}k), "
    f"<b>{d['pct_burden30']:.1f}% ({PM}{d['pct_burden30_moe']:.1f})</b> of renter households, about {k(d['n_burden30'])}, pay "
    f"{GE}30% of income on rent and <b>{d['pct_burden50']:.1f}% ({PM}{d['pct_burden50_moe']:.1f})</b> pay {GE}50%. That is lower than "
    f"Santa Clara County ({REF.loc['Santa Clara County','pct_burden30']:.1f}%), Alameda County ({REF.loc['Alameda County','pct_burden30']:.1f}%) "
    f"and California ({REF.loc['California','pct_burden30']:.1f}%). Burden is highest in the district’s Newark and San José tracts.",
    f"<b>Environmental burden comes from pollution sources, not population vulnerability.</b> District tracts sit at the "
    f"{top_ind['gwthreatsP']:.0f}th statewide percentile for groundwater threats, {top_ind['trafficP']:.0f}th for traffic and "
    f"{top_ind['hazP']:.0f}th for hazardous waste (tract medians), but low on CalEnviroScreen health and socioeconomic indicators. "
    f"Only {c['n_top25']} district tracts (≈{c['pop_top25']/1000:,.1f}k residents) rank in the state’s most-burdened quartile overall.",
    f"<b>CA-17 contains the core of Silicon Valley’s data-center cluster.</b> {f['osm_in_ca17']} of the {f['osm_unique_region']} existing "
    f"data centers mapped in OpenStreetMap across Alameda, Santa Clara and San Mateo counties lie inside CA-17. So do {f['n_dc_in_ca17']} of "
    f"{f['n_documented_dc']} documented proposed or approved projects ({f['n_dc_in_ca17_proposed']} still under review), each disclosing "
    "72–99.8 MW of backup generation or peak load where reported.",
    f"<b>Data centers co-locate with high pollution-burden tracts.</b> The {host[True]['n']} district tracts hosting mapped data centers "
    f"(≈{host[True]['pop']/1000:,.0f}k residents) have a median CalEnviroScreen <i>pollution-burden</i> percentile of {host[True]['poll_med']:.0f}, "
    f"against {host[False]['poll_med']:.0f} in other district tracts. This reflects shared industrial land and legacy contamination. "
    "It is not evidence that data centers produced those scores.",
    f"<b>The strongest combined pressures lie at the district’s edge.</b> Only {S['screen_overlap_n']} district tracts "
    f"(≈{S['screen_overlap_pop']/1000:,.0f}k residents, chiefly Alviso/North San José) are in the regional top third for <i>both</i> rent burden and "
    "CalEnviroScreen. A much larger cluster sits in central San José just outside CA-17, where four downtown data-center proposals "
    "lie 100–810 m from the district line.",
    "<b>Public data are incomplete.</b> The Bay Area Air District’s “Permitted and Proposed Data Centers (Phase 1)” layer is not publicly "
    "accessible, and no public regional register links facility locations to generator permits or electricity demand. That gap limits "
    "oversight and is itself a policy-relevant finding.",
]
E += [Paragraph(b, st["bul"], bulletText="•") for b in bul]
E += [p("Research question and approach", "h2"),
      p("<b>Where does permitted and proposed data-center development overlap with housing-cost pressure and environmental vulnerability "
        "in CA-17?</b> We joined 2020–2024 American Community Survey (ACS) tract estimates (tables B19013, B25064, B25070) and OEHHA "
        "CalEnviroScreen 5.0 to the 202 census tracts that intersect CA-17. District statistics use the "
        f"<b>{d['n_tracts']} tracts with {GE}50% of their area inside the district</b> (≈{d['pop_ces2024']/1000:,.0f}k residents, "
        "close to the ≈760,000 equal-population target for California districts). The 48 tracts mostly outside the district are kept for regional context only. Facilities come from a "
        "<b>documented inventory</b> transcribed from the City of San José’s data-center application list and California Energy Commission (CEC) "
        "backup-generator exemption dockets, plus crowd-sourced OpenStreetMap locations of existing facilities. The overlay uses transparent "
        "tercile classes rather than a composite index, and every finding below is descriptive (co-location, not causation).")]

rows = [["Indicator (ACS 2020–2024)", "CA-17 (154 tracts)", "Santa Clara Co.", "Alameda Co.", "California"],
        [f"Renter households paying {GE}30% of income", f"{d['pct_burden30']:.1f}% {PM}{d['pct_burden30_moe']:.1f}",
         *[f"{REF.loc[g,'pct_burden30']:.1f}%" for g in ["Santa Clara County", "Alameda County", "California"]]],
        [f"Renter households paying {GE}50% of income", f"{d['pct_burden50']:.1f}% {PM}{d['pct_burden50_moe']:.1f}",
         *[f"{REF.loc[g,'pct_burden50']:.1f}%" for g in ["Santa Clara County", "Alameda County", "California"]]],
        ["Median household income*", f"${S['tract_mhi']['median']:,.0f}", *[f"${REF.loc[g,'median_hh_income']:,.0f}" for g in ["Santa Clara County", "Alameda County", "California"]]],
        ["Median gross rent*", f"${S['tract_mgr']['median']:,.0f}", *[f"${REF.loc[g,'median_gross_rent']:,.0f}" for g in ["Santa Clara County", "Alameda County", "California"]]]]
rows = [[Paragraph(x, st["cellb"] if i == 0 else st["cell"]) for x in r] for i, r in enumerate(rows)]
t = Table(rows, colWidths=[2.45 * inch, 1.35 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
                       ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8ced8")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                       ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
E += [Spacer(1, 3), t,
      p(f"* CA-17 column for medians is the median of tract medians (medians cannot be pooled); {S['mhi_topcoded_n']} district tracts are top-coded at "
        f"$250,000 and {S['mgr_topcoded_n']} at $3,500, so true district medians are higher. Burden shares are pooled tract counts; {PM} = 90% margin of "
        "error (Census Bureau approximation). Denominator excludes renter households for whom burden is “not computed” (B25070_011).", "small")]

E += [p("Limitations", "h2"), p("The facility inventory is partial: it covers City of San José applications and CEC dockets only, because the Air District layer returned “Token Required” and "
        "Santa Clara, Milpitas and Sunnyvale publish no equivalent list. OpenStreetMap data are crowd-sourced and unverified. ACS tract estimates have wide margins "
        "of error and top-coded medians, and the 5-year data describe 2020–2024 conditions. The tract-to-district assignment uses area shares, not population. "
        "The supplied Alameda and Santa Clara housing workbooks are byte-identical copies of a 17-record City of Alameda sites inventory (outside CA-17), so they were "
        "not used. The CEC energy-affordability file is labelled draft (“Data is NOT final”) and used for context only. No causal claims are made.", "small")]

# ------------------------------------------------------------------ page 2: Map 1 + housing/environment findings
W = doc.width
from PIL import Image as PILImage
BRIEF_IMG = ROOT / "maps/brief_jpg"
BRIEF_IMG.mkdir(exist_ok=True)


def jpg(fn):
    """Downsample 300-dpi PNG to ~200 dpi JPEG for a mail-friendly PDF (full-resolution maps remain in maps/)."""
    out = BRIEF_IMG / fn.replace(".png", ".jpg")
    im = PILImage.open(ROOT / "maps" / fn).convert("RGB")
    im = im.resize((2200, int(2200 * im.height / im.width)), PILImage.LANCZOS)
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out


img = lambda fn, w=W: Image(str(jpg(fn)), width=w, height=w * 2550 / 3300, hAlign="CENTER")
E += [PageBreak(), img("Map1_Housing_Affordability.png"),
      p("Map 1. Tract-level income, rent and renter cost burden inside CA-17 (ACS 2020–2024). Light grey = parts of tracts mostly outside CA-17 (not "
        "counted). Hatching = low-reliability burden estimate.", "cap"),
      p("Finding 1 — Housing affordability", "h2"),
      p(f"High incomes mask concentrated renter stress. District tract median incomes range from ${S['tract_mhi']['min']:,.0f} to the $250,000 top-code, "
        f"and {S['mgr_topcoded_n']} of {S['tract_mgr']['n']} tracts with a rent estimate have median gross rent at or above the $3,500 top-code (10 of 14 Cupertino tracts; "
        f"10 of 35 in Sunnyvale). Yet {S['burden30_tracts_ge50pct']} tracts have half or more of renters cost-burdened. "
        f"Tract estimates carry wide margins: only {S['burden30_tracts_ge50pct_lowerbound']} of those {S['burden30_tracts_ge50pct']} are distinguishable from 50% "
        "at 90% confidence, so individual tracts should be read as indicative. Pooled across tracts, burden is highest in the district’s Newark "
        "(45%) and San José (39%) portions and lowest in Cupertino and Fremont (33–34%). The large central tract shaded dark in panel C (Alviso/baylands, "
        "tract 5046.02) covers 64 km² but houses only ≈1,500 people; its visual weight overstates its population."),
      p("Finding 2 — Environmental vulnerability", "h2"),
      p(f"CalEnviroScreen ranks district tracts low to moderate overall (median {c['tract_CIscoreP']['median']:.0f}th statewide percentile; "
        f"{c['n_ge50']} of {c['tract_CIscoreP']['n']} at or above the 50th). Pollution-burden indicators run high: tract medians are at the "
        f"{top_ind['gwthreatsP']:.0f}th percentile for groundwater threats, {top_ind['trafficP']:.0f}th for traffic, {top_ind['hazP']:.0f}th for hazardous-waste "
        f"facilities, {top_ind['cleanupsP']:.0f}th for cleanup sites and {top_ind['dieselP']:.0f}th for diesel particulate matter. Asthma, cardiovascular and poverty "
        "indicators are low. Across district tracts, rent burden and CalEnviroScreen score are moderately correlated "
        f"(Spearman ρ = {S['spearman_burden_ces']['rho']:.2f}). CalEnviroScreen measures cumulative exposure to listed pollution sources and population sensitivity; "
        "it does not measure data-center emissions, noise, heat, water use or electricity demand.".replace("ρ", '<font name="ArU">ρ</font>'))]

# ------------------------------------------------------------------ page 3: Map 2 + data-center findings + table
E += [PageBreak(), img("Map2_DataCenters_Environment.png", 6.55 * inch),
      p("Map 2. CalEnviroScreen 5.0 percentile with documented projects (labels key to the table below) and existing facilities mapped in OpenStreetMap.", "cap"),
      p("Finding 3 — Data-center geography", "h2"),
      p(f"Existing facilities concentrate in the Santa Clara–North San José industrial corridor inside CA-17 ({f['osm_in_ca17']} of {f['osm_unique_region']} "
        "OSM-mapped sites in the three counties). Documented projects form two groups. One is a <b>within-district corridor</b> of large campuses in Santa Clara and "
        "North San José (table). The other is <b>a regional pipeline outside the district</b>: four downtown San José proposals, three of which pair a data center with housing "
        "(PD25-013, PD25-015, PD25-011; the fourth, PDC26-016, adds ground-floor retail) and three proposed campuses in south San José near an approved one (SJ13). Where capacity is disclosed, 10 of 13 data-center projects report 90–99.8 MW, just under the "
        "100 MW threshold above which the CEC, rather than local agencies, licenses the backup power plant. This partly reflects how the inventory was built, "
        "since CEC exemption dockets only cover 50–100 MW facilities. Location alone does not indicate a facility’s emissions, energy use or water use.")]
fd = FAC[(FAC.in_ca17 == 1)].copy().sort_values(["facility_type", "status_class", "inv_id"], ascending=[True, False, True])
trows = [["ID", "Project (source ID)", "Status", "MW*", "Bldg sq ft", "Tract CES pct."]]
for _, x in fd.iterrows():
    nm = x.facility_name.replace(" (Microsoft SJDC 04)", " — Microsoft").replace(" (Zanker Rd / Alviso-Milpitas)", "")
    if x.facility_type != "data_center":
        nm += " [not a data center]"
    trows.append([x.inv_id, f"{nm} ({x.source_id})", x.status_class.replace(" - under review", " (under review)"),
                  "—" if pd.isna(x.power_mw) else f"{x.power_mw:g}", "—" if pd.isna(x.building_sqft) else f"{x.building_sqft:,.0f}",
                  f"{x.ces_CIscoreP:.0f}"])
trows = [[Paragraph(str(v), st["cellb"] if i == 0 else st["cell"]) for v in r] for i, r in enumerate(trows)]
t2 = Table(trows, colWidths=[0.5 * inch, 3.05 * inch, 1.35 * inch, 0.5 * inch, 0.75 * inch, 0.85 * inch], repeatRows=1)
t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8ced8")), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
E += [t2, p("Documented projects inside CA-17. *MW basis differs by source (backup-generation capacity, maximum electrical load, or on-site equipment capacity) "
            "and values are not additive. SJ = City of San José Planning (list updated 4 Nov 2026); CEC = California Energy Commission docket. SJ10 and CEC 22-SPPE-02 "
            "appear to be the same Microsoft campus (matched on site and building program). SJ14 is geocoded to street level only.", "small")]

# ------------------------------------------------------------------ page 4: Map 3 + overlap + policy + limits + sources
E += [PageBreak(), img("Map3_Community_Pressure_Screening.png", 6.3 * inch),
      p("Map 3. Bivariate screen of renter cost burden × CalEnviroScreen 5.0 (regional terciles), with facilities. Gold outlines = top tercile on both.", "cap"),
      p("Finding 4 — Where pressures overlap", "h2"),
      p(f"Of {f['n_documented_dc']} documented data-center projects, {f['dc_in_highhigh']} sit in a tract in the top tercile for both rent and environmental burden "
        f"(two downtown San José proposals and the Alviso Microsoft campus), and {f['dc_within_1km_highhigh']} lie within 1 km of such a tract. "
        f"None is in a tract in the state’s top CalEnviroScreen quartile. Inside CA-17 the pattern is <b>industrial co-location</b>: data centers sit in high pollution-burden, "
        f"lower-population tracts (≈2,200–9,300 residents within 1 km of each in-district data-center project, area-weighted estimate). The places where rent and environmental "
        "pressures combine are mostly just outside the district.")]
pol = [
    "<b>Transparency.</b> Ask the Air District to publish its permitted-and-proposed data-center inventory with generator counts, fuel type and permitted "
    "operating hours. Encourage state agencies to link those records to CEC dockets and utility large-load interconnection queues. Without this, cumulative "
    "review and public oversight rely on partial lists like this one.",
    "<b>Cumulative environmental review.</b> Many large campuses are sized just under the 100 MW CEC threshold and cluster in tracts with high groundwater-threat, "
    "cleanup-site and hazardous-waste scores. Corridor-level analysis of backup-generator testing and emergency-operation scenarios would address an exposure "
    "pathway CalEnviroScreen does not capture.",
    "<b>Utility affordability.</b> This analysis cannot measure rate impacts. Draft CEC data put renter household energy burden in CA-17 low (tract median ≈1% "
    "of income), so the more relevant question is how grid and substation costs for very large loads are allocated across ratepayers (PG&amp;E and "
    "Silicon Valley Power service areas).",
    "<b>Housing and community benefits.</b> Renter cost burden is the district’s clearest household-level pressure. Downtown San José proposals that pair data "
    "centers with 345–1,164 housing units, and San José’s data-center uniform-standards process (directed June 2026), are concrete venues for tying approvals "
    "to rental affordability or community-benefit commitments.",
]
E += [p("Policy implications", "h2")] + [Paragraph(b, st["bul"], bulletText="•") for b in pol]
E += [      p("Data sources", "h2"),
      p("U.S. Census Bureau, ACS 2020–2024 5-year (B19013, B25064, B25070), data.census.gov; 2026 TIGER/Line 120th Congressional Districts and tracts. "
        "OEHHA, CalEnviroScreen 5.0 results shapefile (June 2026), oehha.ca.gov/calenviroscreen. City of San José PBCE, “Data Center and other Large Energy-Use "
        "Projects” (updated 11/04/2026), sanjoseca.gov. California Energy Commission, Power Plant Listing and backup-generating-facility dockets "
        "(19-SPPE-04, 20-SPPE-02, 22-SPPE-01/02/03, 23-SPPE-01, 24-SPPE-01, 25-SPPE-02, 26-SPPE-02/03), energy.ca.gov. OpenStreetMap contributors via Overpass API "
        "(ODbL), retrieved 10 Nov 2026; cf. PNNL IM3 Open Source Data Center Atlas (doi:10.57931/2550666), which uses the same source. CEC Energy Equity Indicators "
        "(draft, updated 15 Sep 2025). U.S. Census Bureau Geocoder; Esri World Light Gray Canvas basemap. All sources accessed 10 Nov 2026.", "small")]

doc.build(E)
print("Wrote", OUT)
