"""
05_build_qgis_project.py — Build the QGIS project (qgis/CA17_Tech_Housing.qgz) with organised layers,
symbology and three print layouts, then export each layout to PDF and 300-dpi PNG in maps/.

Run (headless):  source scripts/env.sh && $QGIS_APP/MacOS/python scripts/05_build_qgis_project.py
Requires outputs of scripts 01–04.
"""
import json
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsRectangle,
    QgsGraduatedSymbolRenderer, QgsRendererRange, QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsFillSymbol, QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsRuleBasedRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemScaleBar,
    QgsLayoutItemPicture, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsLayoutExporter, QgsLayerTreeLayer,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling, QgsLayoutItemShape,
    QgsCoordinateTransform, QgsLegendStyle, QgsLayoutMeasurement, Qgis, QgsLayoutItemPage,
    QgsLinePatternFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsLayerTree,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import Qt

ROOT = Path(__file__).resolve().parents[1]
GPKG = ROOT / "data/processed/ca17_analysis.gpkg"
DISP = ROOT / "data/processed/ca17_display.gpkg"
MAPS = ROOT / "maps"
MAPS.mkdir(exist_ok=True)
QGZ = ROOT / "qgis/CA17_Tech_Housing.qgz"
S = json.load(open(ROOT / "data/processed/summary_stats.json"))

app = QgsApplication([], False)
app.setPrefixPath("/Applications/QGIS.app/Contents/MacOS", True)
app.initQgis()
P = QgsProject.instance()
P.clear()
P.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
P.setEllipsoid("EPSG:7030")  # WGS84 ellipsoid -> scale bars measured on the ellipsoid, not Mercator metres
P.setFileName(str(QGZ))
P.writeEntryBool("Paths", "/Absolute", False)
FONT = "Helvetica Neue"

# ------------------------------------------------------------------ display layers (derived, documented)
# Tracts clipped to CA-17 for the district maps; all fields retained.
tr = gpd.read_file(GPKG, layer="ca17_tracts_analysis")
cd = gpd.read_file(GPKG, layer="ca17_district_120th")
clip = gpd.overlay(tr, cd[["geometry"]], how="intersection", keep_geom_type=True)
clip["burden_lowrel"] = ((clip.pct_burden30_cv > 40) | (clip.rent_hh_computed < 50)).astype(int)
if DISP.exists():
    DISP.unlink()
clip.to_file(DISP, layer="ca17_tracts_clipped_display", driver="GPKG")
fac = gpd.read_file(GPKG, layer="facilities_documented")
fac["map_label"] = fac.inv_id
import pandas as pd
cl = pd.read_csv(ROOT / "data/external/osm/city_labels.csv")
# Cartographic offset: move the San José label ~2.5 km ESE of its OSM centroid so it does not cover downtown project symbols
cl.loc[cl.name == "San José", ["lon", "lat"]] = cl.loc[cl.name == "San José", ["lon", "lat"]].values + [0.03, -0.012]
gpd.GeoDataFrame(cl, geometry=gpd.points_from_xy(cl.lon, cl.lat), crs="EPSG:4326").to_crs("EPSG:3857").to_file(
    DISP, layer="city_labels", driver="GPKG")
fac.to_file(DISP, layer="facilities_documented_display", driver="GPKG")


def vlayer(path, layer, name):
    lyr = QgsVectorLayer(f"{path}|layername={layer}", name, "ogr")
    assert lyr.isValid(), f"invalid layer {layer}"
    return lyr


def fill(color, outline="#ffffff", width=0.15, alpha=1.0):
    s = QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width),
                                    "outline_width_unit": "MM"})
    s.setOpacity(alpha)
    return s


def graduated(lyr, field, ranges, nodata_label="No estimate / suppressed", alpha=0.9):
    rr = [QgsRendererRange(lo, hi, fill(c, alpha=alpha), lab) for lo, hi, c, lab in ranges]
    r = QgsGraduatedSymbolRenderer(field, rr)
    lyr.setRenderer(r)
    return lyr


# ------------------------------------------------------------------ basemap
base_tif = QgsRasterLayer(str(ROOT / "data/basemap/esri_World_Light_Gray_Base_z14.tif"), "Esri Light Gray Canvas (cached)")
ref_tif = QgsRasterLayer(str(ROOT / "data/basemap/esri_World_Light_Gray_Reference_z14.tif"), "Esri Light Gray reference labels (cached)")
xyz = QgsRasterLayer("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=16&zmin=0",
                     "Esri Light Gray Canvas (live XYZ)", "wms")
for r in (base_tif, ref_tif):
    assert r.isValid()

# ------------------------------------------------------------------ study area
district = vlayer(GPKG, "ca17_district_120th", "CA-17 (120th Congress boundary, eff. 3 Jan 2027)")
halo = QgsLineSymbol.createSimple({"color": "#ffffff", "width": "1.6"})
halo.appendSymbolLayer(QgsSimpleLineSymbolLayer(QColor("#1a1a1a"), 0.7))
dsym = QgsFillSymbol()
dsym.deleteSymbolLayer(0)
from qgis.core import QgsSimpleFillSymbolLayer
f1 = QgsSimpleFillSymbolLayer(QColor(0, 0, 0, 0), Qt.NoBrush, QColor("#ffffff"), Qt.SolidLine, 1.4)
f2 = QgsSimpleFillSymbolLayer(QColor(0, 0, 0, 0), Qt.NoBrush, QColor("#1a1a1a"), Qt.SolidLine, 0.6)
dsym.appendSymbolLayer(f1)
dsym.appendSymbolLayer(f2)
district.setRenderer(QgsSingleSymbolRenderer(dsym))

counties = vlayer(GPKG, "region_counties", "County boundaries (from CES 5.0 tracts)")
csym = QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#8a8a8a", "outline_width": "0.35",
                                   "outline_style": "dash"})
counties.setRenderer(QgsSingleSymbolRenderer(csym))

tracts_all = vlayer(GPKG, "ca17_tracts_analysis", "CA-17 intersecting tracts (202) — overlap class")
cats = [("1_within (>=90%)", "#4d4d4d", "≥90% of area in CA-17"), ("2_majority (50-90%)", "#8c8c8c", "50–90% (analysis set)"),
        ("3_minority (5-50%)", "#d0b48a", "5–50% (context only)"), ("4_sliver (<5%)", "#e6dccb", "<5% sliver (context only)")]
tracts_all.setRenderer(QgsCategorizedSymbolRenderer("overlap_class", [QgsRendererCategory(v, fill(c, alpha=0.6), l) for v, c, l in cats]))

# ------------------------------------------------------------------ Map 1 layers (clipped tracts)
def clipped(name):
    return vlayer(DISP, "ca17_tracts_clipped_display", name)


GREY = "#d9d9d9"
inc = graduated(clipped("Median household income (B19013)"), "mhi", [
    (0, 124999, "#edf8fb", "< $125,000"), (125000, 174999, "#b3cde3", "$125,000 – 174,999"),
    (175000, 224999, "#8c96c6", "$175,000 – 224,999"), (225000, 249999, "#8856a7", "$225,000 – 249,999"),
    (250000, 10 ** 7, "#5b1f63", "$250,000+ (ACS top-code)")])
inc.setSubsetString('"in_district_set" = 1')
rent = graduated(clipped("Median gross rent (B25064)"), "mgr", [
    (0, 2499, "#fef0d9", "< $2,500"), (2500, 2999, "#fdcc8a", "$2,500 – 2,999"),
    (3000, 3499, "#fc8d59", "$3,000 – 3,499"), (3500, 10 ** 6, "#b30000", "$3,500+ (ACS top-code)")])
rent.setSubsetString('"in_district_set" = 1')
burd = graduated(clipped("Renter households paying ≥30% of income on rent (B25070)"), "pct_burden30", [
    (0, 29.99, "#f2f0f7", "< 30%"), (30, 39.99, "#cbc9e2", "30 – 39.9%"), (40, 49.99, "#9e9ac8", "40 – 49.9%"),
    (50, 59.99, "#756bb1", "50 – 59.9%"), (60, 100, "#54278f", "≥ 60%")])
burd.setSubsetString('"in_district_set" = 1')
lowrel = clipped("Low reliability (CV > 40% or < 50 renter households)")
hs = QgsFillSymbol()
hs.deleteSymbolLayer(0)
lp = QgsLinePatternFillSymbolLayer()
lp.setLineAngle(45)
lp.setDistance(1.2)
lp.setLineWidth(0.25)
lp.setColor(QColor("#222222"))
hs.appendSymbolLayer(lp)
lowrel.setRenderer(QgsSingleSymbolRenderer(hs))
lowrel.setSubsetString('"in_district_set" = 1 AND "burden_lowrel" = 1')
outside = clipped("Tract mostly outside CA-17 (<50% area; not in district statistics)")
outside.setRenderer(QgsSingleSymbolRenderer(fill("#f0f0f0", outline="#bdbdbd", width=0.1)))
outside.setSubsetString('"in_district_set" = 0')
nodata = clipped("No ACS estimate (suppressed / no households)")
nodata.setRenderer(QgsSingleSymbolRenderer(fill("#ffffff", outline="#999999", width=0.1)))
nodata.setSubsetString('"in_district_set" = 1 AND "mhi" IS NULL')

# ------------------------------------------------------------------ Region layers (Map 2/3)
ces = graduated(vlayer(GPKG, "region_tracts_3county", "CalEnviroScreen 5.0 overall percentile (statewide)"), "ces_CIscoreP", [
    (0, 24.99, "#fff7ec", "0 – 24.9 (lowest burden)"), (25, 49.99, "#fdd49e", "25 – 49.9"), (50, 74.99, "#fc8d59", "50 – 74.9"),
    (75, 89.99, "#d7301f", "75 – 89.9"), (90, 100, "#7f0000", "90 – 100 (highest burden)")], alpha=0.78)
BIV = {"1-1": "#e8e8e8", "2-1": "#e4acac", "3-1": "#c85a5a", "1-2": "#b0d5df", "2-2": "#ad9ea5", "3-2": "#985356",
       "1-3": "#64acbe", "2-3": "#627f8c", "3-3": "#574249"}
bivar = vlayer(GPKG, "region_tracts_3county", "Bivariate screen: rent burden × CES 5.0 (regional terciles)")
bcats = [QgsRendererCategory(k, fill(v, alpha=0.85), f"burden T{k[0]} / CES T{k[2]}") for k, v in BIV.items()]
bcats.append(QgsRendererCategory("NA", fill("#ffffff", outline="#bbbbbb", alpha=0.6), "Insufficient data (<50 renter HH or no CES)"))
bivar.setRenderer(QgsCategorizedSymbolRenderer("bivar", bcats))
hh = vlayer(GPKG, "region_tracts_3county", "Screen overlap: top tercile on BOTH burden and CES")
hh.setSubsetString('"screen_overlap" = 1')
hhs = QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#ffcc00", "outline_width": "0.75"})
hh.setRenderer(QgsSingleSymbolRenderer(hhs))

osm = vlayer(GPKG, "datacenters_osm_existing", "Existing data centers mapped in OpenStreetMap (crowd-sourced)")
osm.setSubsetString('"dup_of" IS NULL')
osm.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(
    {"name": "circle", "color": "#4d4d4d", "outline_color": "#ffffff", "outline_width": "0.3", "size": "1.9"})))


def tri(color, outline="#000000"):
    return QgsMarkerSymbol.createSimple({"name": "triangle", "color": color, "outline_color": outline,
                                         "outline_width": "0.35", "size": "4.0"})


facl = vlayer(DISP, "facilities_documented_display", "Documented data-center & large-energy projects (City of San José; CEC)")
fr = QgsRuleBasedRenderer.Rule(None)
for lab, expr, sym in [
    ("Data center — proposed / under review", "\"facility_type\"='data_center' AND \"status_class\"='Proposed - under review'", tri("#f28e2b")),
    ("Data center — approved / CEC-exempted", "\"facility_type\"='data_center' AND \"status_class\"='Approved / exempted'", tri("#1f4e79", "#ffffff")),
    ("Large energy-use project (not a data center)", "\"facility_type\"='large_energy_use_not_dc'",
     QgsMarkerSymbol.createSimple({"name": "square", "color": "#7b3294", "outline_color": "#ffffff", "outline_width": "0.35", "size": "3.2"}))]:
    rule = QgsRuleBasedRenderer.Rule(sym, filterExp=expr, label=lab)
    fr.appendChild(rule)
facl.setRenderer(QgsRuleBasedRenderer(fr))
pal = QgsPalLayerSettings()
pal.fieldName = "map_label"
tf = QgsTextFormat()
tf.setFont(QFont(FONT, 6))
tf.setSize(6.0)
tf.setColor(QColor("#111111"))
bf = QgsTextBufferSettings()
bf.setEnabled(True)
bf.setSize(0.8)
bf.setColor(QColor("#ffffff"))
tf.setBuffer(bf)
pal.setFormat(tf)
pal.placement = Qgis.LabelPlacement.OrderedPositionsAroundPoint
pal.dist = 0.8
facl.setLabeling(QgsVectorLayerSimpleLabeling(pal))
facl.setLabelsEnabled(True)

cities = vlayer(DISP, "city_labels", "City labels")
cities.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({"name": "circle", "size": "0", "color": "0,0,0,0", "outline_style": "no"})))
cpal = QgsPalLayerSettings()
cpal.fieldName = "name"
ctf = QgsTextFormat()
cfont = QFont(FONT)
cfont.setItalic(True)
ctf.setFont(cfont)
ctf.setSize(7.5)
ctf.setColor(QColor("#3a3a3a"))
cbf = QgsTextBufferSettings()
cbf.setEnabled(True)
cbf.setSize(1.0)
cbf.setColor(QColor(255, 255, 255, 220))
ctf.setBuffer(cbf)
cpal.setFormat(ctf)
cpal.placement = Qgis.LabelPlacement.OverPoint
cpal.priority = 10
cpal.displayAll = True
cities.setLabeling(QgsVectorLayerSimpleLabeling(cpal))
cities.setLabelsEnabled(True)

# ------------------------------------------------------------------ layer tree (organised groups)
root = P.layerTreeRoot()
groups = {}
for g in ["Facilities & data centers", "Integrated screening (Map 3)", "Environmental vulnerability (Map 2)",
          "Housing affordability (Map 1)", "Study area & tract coverage", "Basemap"]:
    groups[g] = root.addGroup(g)


def add(lyr, g, visible=True):
    P.addMapLayer(lyr, False)
    node = groups[g].addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    return lyr


for l in (facl, osm):
    add(l, "Facilities & data centers")
add(cities, "Study area & tract coverage")
add(hh, "Integrated screening (Map 3)")
add(bivar, "Integrated screening (Map 3)", False)
add(ces, "Environmental vulnerability (Map 2)", False)
for l in (lowrel, nodata, outside, burd, rent, inc):
    add(l, "Housing affordability (Map 1)", l in (lowrel, nodata, outside))
add(district, "Study area & tract coverage")
add(counties, "Study area & tract coverage")
add(tracts_all, "Study area & tract coverage", False)
add(ref_tif, "Basemap")
add(base_tif, "Basemap")
add(xyz, "Basemap", False)
ref_tif.setOpacity(0.9)

# ------------------------------------------------------------------ bivariate legend graphic
fig, ax = plt.subplots(figsize=(1.9, 1.9), dpi=300)
for k, v in BIV.items():
    b, c = int(k[0]), int(k[2])
    ax.add_patch(plt.Rectangle((b - 1, c - 1), 1, 1, color=v, ec="white", lw=1.2))
ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.set_aspect("equal")
ax.set_xticks([0.5, 1.5, 2.5]); ax.set_xticklabels(["low", "mid", "high"], fontsize=6)
ax.set_yticks([0.5, 1.5, 2.5]); ax.set_yticklabels(["low", "mid", "high"], fontsize=6)
ax.set_xlabel("Renter cost burden (≥30%) →", fontsize=6.5)
ax.set_ylabel("CalEnviroScreen 5.0 →", fontsize=6.5)
for s_ in ax.spines.values(): s_.set_visible(False)
ax.tick_params(length=0, pad=1.5)
plt.tight_layout(pad=0.2)
BIVPNG = MAPS / "legend_bivariate.png"
fig.savefig(BIVPNG, transparent=True)
plt.close(fig)


# ------------------------------------------------------------------ layout helpers
def to3857(xmin, ymin, xmax, ymax):
    t = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), QgsCoordinateReferenceSystem("EPSG:3857"), P)
    return t.transformBoundingBox(QgsRectangle(xmin, ymin, xmax, ymax))


def label(layout, text, x, y, w, h, size=8, bold=False, color="#222222", html=False, align=Qt.AlignLeft):
    it = QgsLayoutItemLabel(layout)
    it.setText(text)
    f = QFont(FONT)
    f.setBold(bold)
    tf_ = QgsTextFormat()
    tf_.setFont(f)
    tf_.setSize(size)
    tf_.setColor(QColor(color))
    it.setTextFormat(tf_)
    if html:
        it.setMode(QgsLayoutItemLabel.ModeHtml)
    it.setHAlign(align)
    it.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    it.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(it)
    return it


def mapitem(layout, layers, extent, x, y, w, h, frame=True):
    m = QgsLayoutItemMap(layout)
    m.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    m.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    m.setLayers(layers)
    m.setKeepLayerSet(True)
    m.zoomToExtent(extent)
    m.setFrameEnabled(frame)
    m.setFrameStrokeColor(QColor("#9a9a9a"))
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.25))
    layout.addLayoutItem(m)
    return m


def scalebar(layout, m, x, y, km=5):
    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Single Box")
    sb.setLinkedMap(m)
    sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel("km")
    sb.setUnitsPerSegment(km)
    sb.setNumberOfSegments(2)
    sb.setNumberOfSegmentsLeft(0)
    sb.setHeight(1.5)
    tf_ = QgsTextFormat()
    tf_.setFont(QFont(FONT))
    tf_.setSize(6.5)
    sb.setTextFormat(tf_)
    sb.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(sb)
    return sb


def north(layout, x, y, s=9):
    p = QgsLayoutItemPicture(layout)
    p.setPicturePath("/Applications/QGIS.app/Contents/Resources/qgis/svg/arrows/NorthArrow_04.svg")
    p.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    p.attemptResize(QgsLayoutSize(s, s, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(p)
    return p


def legend(layout, layers, m, x, y, w, title="", fsize=7):
    lg = QgsLayoutItemLegend(layout)
    lg.setTitle(title)
    lg.setLinkedMap(m)
    lg.setAutoUpdateModel(False)
    rg = lg.model().rootGroup()
    rg.removeAllChildren()
    for l in layers:
        rg.addLayer(l)
    for st, sz, b in [(QgsLegendStyle.Title, 8.5, True), (QgsLegendStyle.Group, 7.5, True),
                      (QgsLegendStyle.Subgroup, 7, True), (QgsLegendStyle.SymbolLabel, fsize, False)]:
        tf_ = QgsTextFormat()
        f = QFont(FONT)
        f.setBold(b)
        tf_.setFont(f)
        tf_.setSize(sz)
        lg.rstyle(st).setTextFormat(tf_)
    lg.setSymbolWidth(5)
    lg.setSymbolHeight(3.0)
    for st in (QgsLegendStyle.Symbol, QgsLegendStyle.SymbolLabel):
        lg.rstyle(st).setMargin(QgsLegendStyle.Top, 0.9)
    lg.rstyle(QgsLegendStyle.Group).setMargin(QgsLegendStyle.Top, 2.0)
    lg.setWrapString("|")
    lg.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    lg.setResizeToContents(True)
    lg.setBackgroundEnabled(False)
    layout.addLayoutItem(lg)
    lg.adjustBoxSize()
    return lg


def new_layout(name):
    old = P.layoutManager().layoutByName(name)
    if old:
        P.layoutManager().removeLayout(old)
    lay = QgsPrintLayout(P)
    lay.initializeDefaults()
    lay.setName(name)
    lay.pageCollection().page(0).setPageSize("Letter", QgsLayoutItemPage.Landscape)  # 279.4 x 215.9 mm
    P.layoutManager().addLayout(lay)
    return lay


BASE = [ref_tif, base_tif]
SRC_FOOT = ("Basemap: Esri World Light Gray Canvas (Esri, HERE, Garmin, © OpenStreetMap contributors). "
            "District: U.S. Census Bureau 2026 TIGER/Line, 120th Congress CD (effective 3 Jan 2027). Projection: Web Mercator; scale bar measured on WGS84 ellipsoid.")

# ================================================================== MAP 1 — Housing affordability
L1 = new_layout("Map 1 – Housing affordability")
label(L1, "Map 1. Housing affordability in CA-17", 10, 7, 200, 9, 15, True)
label(L1, "Median household income, median gross rent, and renter cost burden by census tract — ACS 2020–2024 5-year estimates", 10, 15.5, 260, 6, 9, color="#555555")
ext1 = cd.to_crs(4326).total_bounds
e1 = to3857(ext1[0] - 0.012, ext1[1] - 0.008, ext1[2] + 0.012, ext1[3] + 0.008)
pw, ph, py = 84, 116, 24
panels = [(inc, "A. Median household income", 10), (rent, "B. Median gross rent", 97.5), (burd, "C. Renters paying ≥30% of income on rent", 185)]
for lyr, ttl, px in panels:
    extra = [lowrel] if lyr is burd else []
    m = mapitem(L1, [cities, district] + extra + [nodata, lyr, outside] + BASE, e1, px, py, pw, ph)
    label(L1, ttl, px, py + ph + 1.5, pw, 5, 8.5, True)
    extra_leg = [lowrel] if lyr is burd else ([outside, nodata] if lyr is inc else [])
    legend(L1, [lyr] + extra_leg, m, px, py + ph + 6.5, pw, fsize=6.8)
    if px == 10:
        scalebar(L1, m, px + 2, py + ph - 9, km=4)
        north(L1, px + pw - 11, py + 2, 8)
d = S["district_set"]
notes1 = (f"District statistics use the {d['n_tracts']} tracts with ≥50% of their area in CA-17 (≈{d['pop_ces2024']/1000:.0f}k residents). "
          f"Light grey = tract parts belonging to tracts mostly outside CA-17 (shown, not counted). ACS top-codes medians at $250,000 (income) and $3,500 (rent): "
          f"{S['mhi_topcoded_n']} and {S['mgr_topcoded_n']} district tracts respectively are top-coded, so the top class is a floor, not a value. "
          "Cost burden = (B25070_007–010) ÷ (B25070_001 − B25070_011 'not computed'). Hatching marks tracts with CV > 40% or < 50 renter households.")
label(L1, notes1, 10, 187, 259, 12, 6.4, color="#333333")
label(L1, "Sources: U.S. Census Bureau ACS 2020–2024 5-year, tables B19013, B25064, B25070 (tract). " + SRC_FOOT, 10, 201, 259, 9, 6, color="#666666")

# ================================================================== region extent
e2 = to3857(-122.105, 37.215, -121.725, 37.575)

# ================================================================== MAP 2 — Technology infrastructure & environment
L2 = new_layout("Map 2 – Data centers and environmental vulnerability")
label(L2, "Map 2. Data-center development and environmental vulnerability", 10, 7, 260, 9, 15, True)
label(L2, "CalEnviroScreen 5.0 overall percentile (statewide ranking) with documented data-center projects and OSM-mapped existing facilities", 10, 15.5, 260, 6, 9, color="#555555")
m2 = mapitem(L2, [cities, facl, osm, district, counties, ces] + BASE, e2, 10, 24, 168, 176)
scalebar(L2, m2, 13, 190, km=5)
north(L2, 166, 27, 9)
legend(L2, [district, facl, osm, ces], m2, 183, 24, 90, fsize=6.8)
f = S["fac"]
notes2 = (f"Documented inventory: {f['n_documented_dc']} data-center projects ({f['n_dc_proposed']} proposed/under review) and {f['n_leu']} large energy-use projects, "
          f"transcribed from the City of San José Planning list (updated 4 Nov 2026) and CEC Small Power Plant Exemption dockets; labels (SJ##/CEC##) key to the briefing table. "
          f"{f['n_dc_in_ca17']} documented data centers and {f['osm_in_ca17']} OSM-mapped existing facilities fall inside CA-17. "
          "The inventory is NOT comprehensive: the Bay Area Air District 'Permitted and Proposed Data Centers (Phase 1)' layer was not publicly accessible, "
          "and other cities (e.g., Santa Clara, Milpitas) do not publish equivalent lists. Locations are not evidence of emissions, energy or water use.")
label(L2, notes2, 183, 128, 90, 60, 6.5, color="#333333")
label(L2, "Sources: OEHHA CalEnviroScreen 5.0 (2026); City of San José PBCE; California Energy Commission; OpenStreetMap contributors via Overpass API "
      "(retrieved 10 Nov 2026; ODbL). " + SRC_FOOT, 10, 202, 263, 9, 6, color="#666666")

# ================================================================== MAP 3 — Community pressure screening
L3 = new_layout("Map 3 – Community pressure screening")
label(L3, "Map 3. Community pressure screening: rent burden × environmental burden × data centers", 10, 7, 265, 9, 15, True)
label(L3, "Tracts classified by regional (Alameda, Santa Clara, San Mateo) terciles of renter cost burden and CalEnviroScreen 5.0 percentile", 10, 15.5, 260, 6, 9, color="#555555")
m3 = mapitem(L3, [cities, facl, osm, hh, district, counties, bivar] + BASE, e2, 10, 24, 168, 176)
scalebar(L3, m3, 13, 190, km=5)
north(L3, 166, 27, 9)
pic = QgsLayoutItemPicture(L3)
pic.setPicturePath(str(BIVPNG))
pic.attemptMove(QgsLayoutPoint(186, 24, QgsUnitTypes.LayoutMillimeters))
pic.attemptResize(QgsLayoutSize(42, 42, QgsUnitTypes.LayoutMillimeters))
L3.addLayoutItem(pic)
legend(L3, [district, hh, facl, osm], m3, 183, 68, 90, fsize=6.8)
cuts = "rent burden terciles at 41.1% and 55.1%; CES terciles at the 21.3 and 46.0 statewide percentiles"
notes3 = (f"Tercile cut points ({cuts}) are computed across all 959 tracts in the three counties, so 'high' is relative to the regional market. "
          f"Tracts with <50 renter households are not classified. Gold outline = top tercile on both measures; {S['screen_overlap_n']} district-set tracts "
          f"(≈{S['screen_overlap_pop']/1000:.0f}k residents) meet this test. This is a screening overlay, not a composite index: it identifies where pressures co-occur, "
          "not why, and facility proximity does not imply exposure or causation.")
label(L3, notes3, 183, 132, 90, 60, 6.5, color="#333333")
label(L3, "Sources: ACS 2020–2024 B25070; OEHHA CalEnviroScreen 5.0; City of San José PBCE; CEC; OpenStreetMap contributors. " + SRC_FOOT, 10, 202, 263, 9, 6, color="#666666")

# ------------------------------------------------------------------ save + export
P.write(str(QGZ))
print("Saved", QGZ)
for lay, fn in [(L1, "Map1_Housing_Affordability"), (L2, "Map2_DataCenters_Environment"), (L3, "Map3_Community_Pressure_Screening")]:
    ex = QgsLayoutExporter(lay)
    ps = QgsLayoutExporter.PdfExportSettings()
    ps.dpi = 300
    ps.rasterizeWholeImage = False
    r1 = ex.exportToPdf(str(MAPS / f"{fn}.pdf"), ps)
    is_ = QgsLayoutExporter.ImageExportSettings()
    is_.dpi = 300
    r2 = ex.exportToImage(str(MAPS / f"{fn}.png"), is_)
    print(fn, "pdf:", r1, "png:", r2)
app.exitQgis()
