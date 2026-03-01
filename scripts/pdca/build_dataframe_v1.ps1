$ErrorActionPreference = "Stop"

$python = "C:/Users/user/keiba-local3/.venv/Scripts/python.exe"

& $python scripts/pdca/build_dataframe.py --start-year 2020 --end-year 2026 --dataset-version df_v001
