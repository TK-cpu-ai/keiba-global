# scripts/fetch_pedigree_5gen.py

import time
import random
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)"
]

BASE_URL = "https://db.netkeiba.com/horse/ped/"

BASE_DIR = Path("derived")
MASTER_PATH = BASE_DIR / "masters" / "horses.json"
PED_DIR = BASE_DIR / "pedigree"
PED_DIR.mkdir(parents=True, exist_ok=True)

PKL_PATH = PED_DIR / "peds_5gen.pkl"
JSON_PATH = PED_DIR / "peds_5gen.json"


def fetch_one_pedigree(horse_id: str) -> list[dict]:
    url = BASE_URL + horse_id + "/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    r.encoding = "EUC-JP"

    soup = BeautifulSoup(r.text, "lxml")

    table = soup.select_one("table.blood_table")
    if table is None:
        raise RuntimeError("pedigree table not found")

    records = []

    for tr in table.find_all("tr"):
        for td in tr.find_all("td"):
            a = td.find("a", href=True)

            if a:
                ancestor_id = a["href"].rstrip("/").split("/")[-1]
                name = a.get_text(strip=True)
            else:
                ancestor_id = None
                name = td.get_text(strip=True)

            if name:
                records.append({
                    "horse_id": ancestor_id,
                    "name": name
                })

    if len(records) < 40:
        raise RuntimeError(f"too few pedigree cells: {len(records)}")

    return records[:62]


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_atomic(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def main():
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

            existing[horse_id] = {
                f"peds_{i}": r for i, r in enumerate(records)
            }

            # ★ ここで即JSON保存（途中停止対策）
            save_json_atomic(JSON_PATH, existing)

            s = pd.Series(
                [r["horse_id"] for r in records],
                index=[f"peds_{i}" for i in range(len(records))],
                name=horse_id
            )
            rows.append(s)

            print(f"  ✓ fetched & saved: {len(records)}")

        except Exception as e:
            print(f"  ⚠ ERROR {horse_id}: {e}")

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
