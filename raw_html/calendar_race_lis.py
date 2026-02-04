import requests
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup

BASE_CALENDAR_URL = "https://race.netkeiba.com/top/calendar.html"
BASE_RACE_LIST_SP = "https://race.sp.netkeiba.com/"

SAVE_DIR_CAL = Path("raw_html/calendar")
SAVE_DIR_LIST = Path("raw_html/race_list")
SAVE_DIR_ID = Path("raw_html/race_id")

START_YEAR = 2019
END_YEAR = 2019

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

for d in (SAVE_DIR_CAL, SAVE_DIR_LIST, SAVE_DIR_ID):
    d.mkdir(parents=True, exist_ok=True)


def fetch_pc(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS_PC, timeout=15)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def fetch_sp(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS_SP, timeout=15)
    r.raise_for_status()
    r.encoding = "shift_jis"   # ← ここが超重要
    return r.text


def save_calendar(year: int, month: int) -> list[str]:
    print(f"[CALENDAR] {year}-{month:02d}")

    html = fetch_pc(BASE_CALENDAR_URL, {
        "year": year,
        "month": month
    })

    path = SAVE_DIR_CAL / f"calendar_{year}_{month:02d}.html"
    path.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")

    dates = set()
    for a in soup.select("a[href*='kaisai_date=']"):
        href = a.get("href")
        date = href.split("kaisai_date=")[-1]
        if date.isdigit():
            dates.add(date)

    return sorted(dates)


def save_race_list(kaisai_date: str):
    print(f"  [RACE_LIST] {kaisai_date}")

    html = fetch_sp(BASE_RACE_LIST_SP, {
        "pid": "race_list",
        "kaisai_date": kaisai_date
    })

    path = SAVE_DIR_LIST / f"race_list_{kaisai_date}.html"
    path.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")

    race_ids = set()
    for a in soup.select("a[href*='/race/']"):
        m = re.search(r"/race/(\d+)/", a.get("href", ""))
        if m:
            race_ids.add(m.group(1))

    id_path = SAVE_DIR_ID / f"race_id_{kaisai_date}.txt"
    id_path.write_text("\n".join(sorted(race_ids)), encoding="utf-8")


def main():
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            dates = save_calendar(year, month)
            time.sleep(2)

            for d in dates:
                save_race_list(d)
                time.sleep(2)


if __name__ == "__main__":
    main()
