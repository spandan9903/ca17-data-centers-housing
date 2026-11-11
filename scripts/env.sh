# Source this to use QGIS's bundled Python (PyQGIS + GeoPandas)
export QGIS_APP=/Applications/QGIS.app/Contents
export PROJ_DATA=$QGIS_APP/Resources/qgis/proj
export PROJ_LIB=$PROJ_DATA
export GDAL_DATA=$QGIS_APP/Resources/qgis/gdal
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_pylib:$PYTHONPATH"
export QT_QPA_PLATFORM=offscreen
alias qpy="$QGIS_APP/MacOS/python"
