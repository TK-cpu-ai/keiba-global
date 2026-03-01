from __future__ import annotations

import argparse
import json
import re
import time

import requests
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from requests.exceptions import RequestException

from keiba.config.paths import RAW_RACE_ID_DIR, ensure_core_dirs


BASE_CALENDAR_URL = "https://race.netkeiba.com/top/calendar.html"
BASE_RACE_LIST_SP = "https://race.sp.netkeiba.com/"

HEADERS_SP = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile Safari/604.1"
    )
}

HEADERS_PC = {"User-Agent": "Mozilla/5.0"}

RETRY = 3
RETRY_SLEEP = 10


def fetch_pc(url, params=None) -> str | None:
    for i in range(RETRY):
        try:
            response = requests.get(url, params=params, headers=HEADERS_PC, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except RequestException as exc:
            print(f"    ⚠ fetch_pc failed ({i + 1}/{RETRY}): {exc}")
            time.sleep(RETRY_SLEEP)
    return None


def fetch_sp(url, params=None) -> str | None:
    for i in range(RETRY):
        try:
            response = requests.get(url, params=params, headers=HEADERS_SP, timeout=15)
            response.raise_for_status()

            result = from_bytes(response.content).best()
            if result is None:
                return response.content.decode("utf-8", errors="replace")
            return str(result)

        except RequestException as exc:
            print(f"    ⚠ fetch_sp failed ({i + 1}/{RETRY}): {exc}")
            time.sleep(RETRY_SLEEP)

    return None


def fetch_calendar_dates(year: int, month: int) -> list[str]:
    print(f"[CALENDAR] {year}-{month:02d}")
    html = fetch_pc(BASE_CALENDAR_URL, {"year": year, "month": month})

    if html is None:
        print("    ⚠ calendar fetch failed, skip month")
        return []

    soup = BeautifulSoup(html, "html.parser")

    dates = set()
    for anchor in soup.select("a[href*='kaisai_date=']"):
        href = anchor.get("href", "")
        date = href.split("kaisai_date=")[-1]
        if date.isdigit():
            dates.add(date)

    return sorted(dates)


def fetch_race_ids(kaisai_date: str) -> set[str]:
    print(f"  [RACE_LIST] {kaisai_date}")
    html = fetch_sp(BASE_RACE_LIST_SP, {"pid": "race_list", "kaisai_date": kaisai_date})

    if html is None:
        print("    ⚠ race_list fetch failed, skip date")
        return set()

    soup = BeautifulSoup(html, "html.parser")
    race_ids: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")

        match = re.search(r"race_id=(\d+)", href)
        if match:
            race_ids.add(match.group(1))
            continue

        match = re.search(r"/race/(\d+)/", href)
        if match:
            race_ids.add(match.group(1))

    if not race_ids:
        print("    ⚠ race_id が1件も取れていません（HTML構造変更の可能性）")

    return race_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch race IDs and save yearly files.")
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_core_dirs()

    for year in range(args.start_year, args.end_year + 1):
        print(f"\n=== {year} ===")

        txt_path = RAW_RACE_ID_DIR / f"race_id_{year}.txt"
        json_path = RAW_RACE_ID_DIR / f"race_id_map_{year}.json"

        if json_path.exists():
            race_map = json.loads(json_path.read_text(encoding="utf-8"))
            print(f"    loaded existing map: {len(race_map)} dates")
        else:
            race_map = {}

        for month in range(1, 13):
            dates = fetch_calendar_dates(year, month)
            time.sleep(2)

            for date in dates:
                if date in race_map:
                    continue

                race_ids = fetch_race_ids(date)
                race_map[date] = sorted(race_ids)
                time.sleep(2)

        all_race_ids = set()
        for ids in race_map.values():
            all_race_ids.update(ids)

        txt_path.write_text("\n".join(sorted(all_race_ids)), encoding="utf-8")
        json_path.write_text(
            json.dumps(race_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[SAVED] {txt_path} ({len(all_race_ids)} races)")
        print(f"[SAVED] {json_path} ({len(race_map)} dates)")


if __name__ == "__main__":
    main()
