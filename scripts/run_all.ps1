# Windows equivalent of run_all.sh
$ErrorActionPreference = "Stop"
python -m payequity all --scale starter
python -m payequity all --scale full
python -m payequity reproduce --scale starter
