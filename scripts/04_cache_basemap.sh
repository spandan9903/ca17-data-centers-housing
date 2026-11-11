#!/bin/bash
# Cache Esri World Light Gray Canvas (base + reference labels) to local GeoTIFFs (EPSG:3857, ~9.55 m/px ≈ zoom 14)
# for reproducible offline map export. Source: Esri, HERE, Garmin, (c) OpenStreetMap contributors, and the GIS user community.
cd "$(dirname "$0")/.." && source scripts/env.sh
PROJWIN="-13603683 4537000 -13536866 4455000"   # approx lon -122.20..-121.60, lat 37.10..37.72
for L in World_Light_Gray_Base World_Light_Gray_Reference; do
  $QGIS_APP/MacOS/gdal_translate -q -projwin $PROJWIN -tr 9.55 9.55 -co COMPRESS=DEFLATE -co TILED=YES \
     data/basemap/esri_$L.xml data/basemap/esri_${L}_z14.tif &
done
wait
