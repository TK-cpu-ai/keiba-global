import requests
import time
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from requests.exceptions import RequestException

# =====================
# 設定
# =====================

BASE_CALENDAR_URL = "https://race.netkeiba.com/top/calendar.html"
BASE_RACE_LIST_SP = "https://race.sp.netkeiba.com/"

START_YEAR = 2026
END_YEAR = 2026

OUTPUT_BASE_DIR = Path("data/raw/race_id")

HEADERS_SP = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile Safari/604.1"
    )
}

HEADERS_PC = {
    "User-Agent": "Mozilla/5.0"
}

RETRY = 3
RETRY_SLEEP = 10


# =====================
# fetch系（変更なし）
# =====================

def fetch_pc(url, params=None) -> str | None:
    for i in range(RETRY):
        try:
            r = requests.get(url, params=params, headers=HEADERS_PC, timeout=15)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except RequestException as e:
            print(f"    ⚠ fetch_pc failed ({i+1}/{RETRY}): {e}")
            time.sleep(RETRY_SLEEP)
    return None


def fetch_sp(url, params=None) -> str | None:
    for i in range(RETRY):
        try:
            r = requests.get(url, params=params, headers=HEADERS_SP, timeout=15)
            r.raise_for_status()

            raw = r.content
            result = from_bytes(raw).best()

            if result is None:
                return raw.decode("utf-8", errors="replace")

            return str(result)

        except RequestException as e:
            print(f"    ⚠ fetch_sp failed ({i+1}/{RETRY}): {e}")
            time.sleep(RETRY_SLEEP)

    return None


# =====================
# calendar（変更なし）
# =====================

def fetch_calendar_dates(year: int, month: int) -> list[str]:
    print(f"[CALENDAR] {year}-{month:02d}")

    html = fetch_pc(
        BASE_CALENDAR_URL,
        {"year": year, "month": month}
    )

    if html is None:
        print("    ⚠ calendar fetch failed, skip month")
        return []

    soup = BeautifulSoup(html, "html.parser")

    dates = set()
    for a in soup.select("a[href*='kaisai_date=']"):
        href = a.get("href", "")
        date = href.split("kaisai_date=")[-1]
        if date.isdigit():
            dates.add(date)

    return sorted(dates)


# =====================
# race_list → race_id（変更なし）
# =====================

def fetch_race_ids(kaisai_date: str) -> set[str]:
    print(f"  [RACE_LIST] {kaisai_date}")

    html = fetch_sp(
        BASE_RACE_LIST_SP,
        {"pid": "race_list", "kaisai_date": kaisai_date}
    )

    if html is None:
        print("    ⚠ race_list fetch failed, skip date")
        return set()

    soup = BeautifulSoup(html, "html.parser")

    race_ids = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")

        m = re.search(r"race_id=(\d+)", href)
        if m:
            race_ids.add(m.group(1))
            continue

        m = re.search(r"/race/(\d+)/", href)
        if m:
            race_ids.add(m.group(1))

    if not race_ids:
        print("    ⚠ race_id が1件も取れてない（HTML構造変更の可能性）")

    return race_ids


# =====================
# main（★ここだけ差分更新追加）
# =====================

def main():
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    for year in range(START_YEAR, END_YEAR + 1):
        print(f"\n=== {year} ===")

        txt_path = OUTPUT_BASE_DIR / f"race_id_{year}.txt"
        json_path = OUTPUT_BASE_DIR / f"race_id_map_{year}.json"

        # 既存マップ読み込み（なければ空）
        if json_path.exists():
            race_map = json.loads(json_path.read_text(encoding="utf-8"))
            print(f"    loaded existing map: {len(race_map)} dates")
        else:
            race_map = {}

        for month in range(1, 13):
            dates = fetch_calendar_dates(year, month)
            time.sleep(2)

            for d in dates:

                # ★ 既に取得済みの開催日はスキップ
                if d in race_map:
                    continue

                race_ids = fetch_race_ids(d)
                race_map[d] = sorted(race_ids)
                time.sleep(2)

        # --- txt 用に全集約 ---
        all_race_ids = set()
        for ids in race_map.values():
            all_race_ids.update(ids)

        txt_path.write_text(
            "\n".join(sorted(all_race_ids)),
            encoding="utf-8"
        )

        json_path.write_text(
            json.dumps(race_map, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[SAVED] {txt_path} ({len(all_race_ids)} races)")
        print(f"[SAVED] {json_path} ({len(race_map)} dates)")


if __name__ == "__main__":
    main()
