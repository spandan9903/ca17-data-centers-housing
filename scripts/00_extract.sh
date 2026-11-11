#!/bin/bash
# Unzip the supplied ACS and CalEnviroScreen archives into data/extracted/ (one folder per archive).
cd "$(dirname "$0")/.."
for z in data/raw/*.zip; do d="data/extracted/$(basename "${z%.zip}")"; mkdir -p "$d"; unzip -o -q "$z" -d "$d"; done
echo "Extracted to data/extracted/"
