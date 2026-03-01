from __future__ import annotations

import json
import random
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from keiba.config.paths import IMMUTABLE_MASTERS_DIR, IMMUTABLE_PEDIGREE_DIR, ensure_core_dirs


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

BASE_URL = "https://db.netkeiba.com/horse/ped/"

MASTER_PATH = IMMUTABLE_MASTERS_DIR / "horses.json"
PKL_PATH = IMMUTABLE_PEDIGREE_DIR / "peds_5gen.pkl"
JSON_PATH = IMMUTABLE_PEDIGREE_DIR / "peds_5gen.json"


def fetch_one_pedigree(horse_id: str) -> list[dict]:
    url = BASE_URL + horse_id + "/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    response.encoding = "EUC-JP"

    soup = BeautifulSoup(response.text, "lxml")
    table = soup.select_one("table.blood_table")
    if table is None:
        raise RuntimeError("pedigree table not found")

    records = []
    for tr in table.find_all("tr"):
        for td in tr.find_all("td"):
            anchor = td.find("a", href=True)

            if anchor:
                ancestor_id = anchor["href"].rstrip("/").split("/")[-1]
                name = anchor.get_text(strip=True)
            else:
                ancestor_id = None
                name = td.get_text(strip=True)

            if name:
                records.append({"horse_id": ancestor_id, "name": name})

    if len(records) < 40:
        raise RuntimeError(f"too few pedigree cells: {len(records)}")

    return records[:62]


def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def main() -> None:
    ensure_core_dirs()

    if not MASTER_PATH.exists():
        raise FileNotFoundError(f"master not found: {MASTER_PATH}")

    with open(MASTER_PATH, encoding="utf-8") as f:
        horses = json.load(f)

    existing = load_json(JSON_PATH)
    rows = []

    print("JSON save path:", JSON_PATH.resolve())
    print("PKL  save path:", PKL_PATH.resolve())

    for horse_id in horses.keys():
        if horse_id in existing:
            continue

        print(f"[FETCH] {horse_id}")
        time.sleep(1)

        try:
            records = fetch_one_pedigree(horse_id)

            existing[horse_id] = {f"peds_{i}": r for i, r in enumerate(records)}
            save_json_atomic(JSON_PATH, existing)

            series = pd.Series(
                [r["horse_id"] for r in records],
                index=[f"peds_{i}" for i in range(len(records))],
                name=horse_id,
            )
            rows.append(series)

            print(f"  ✓ fetched & saved: {len(records)}")

        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ ERROR {horse_id}: {exc}")

    if rows:
        df = pd.DataFrame(rows)
        if PKL_PATH.exists():
            old = pd.read_pickle(PKL_PATH)
            df = pd.concat([old, df])
        df.to_pickle(PKL_PATH)
        print("PKL updated")

    print("done")


if __name__ == "__main__":
    main()
