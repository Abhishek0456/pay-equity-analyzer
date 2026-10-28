#!/usr/bin/env sh
# Generate, analyze, validate and export the starter + full datasets, then check reproducibility.
set -e
python -m payequity all --scale starter
python -m payequity all --scale full
python -m payequity reproduce --scale starter
