import csv
import time
import random
import pathlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================
# 設定
# =====================
RACE_ID_CSV = r"C:\Users\user\keiba-local\output\race_ids_2019.csv"
OUTPUT_ROOT = pathlib.Path("output/html/race")
TARGET_YEAR = "2019"
TARGET_MONTH = "05"   # ← 検証時はここだけ変える

BASE_URL = "https://race.netkeiba.com/race/result.html?race_id={}"

WAIT_MIN = 0.5
WAIT_MAX = 1.5
TIMEOUT = 10

# =====================
# Session 構築
# =====================
def create_session():
    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://race.netkeiba.com/",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    session.headers.update(headers)

    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

# =====================
# race_id 読み込み
# =====================
def load_race_ids():
    race_ids = []
    with open(RACE_ID_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            race_id = row["race_id"]
            if race_id.startswith(TARGET_YEAR) and race_id[4:6] == TARGET_MONTH:
                race_ids.append(race_id)
    return race_ids

# =====================
# メイン処理
# =====================
def main():
    session = create_session()
    race_ids = load_race_ids()

    print(f"[INFO] target races: {len(race_ids)}")

    for i, race_id in enumerate(race_ids, 1):
        url = BASE_URL.format(race_id)

        out_dir = OUTPUT_ROOT / TARGET_YEAR / TARGET_MONTH
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"{race_id}.html"
        if out_file.exists():
            continue

        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()

            out_file.write_bytes(resp.content)
            print(f"[{i}/{len(race_ids)}] saved {race_id}")

        except Exception as e:
            print(f"[ERROR] {race_id} : {e}")

        time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))

    print("[DONE]")

if __name__ == "__main__":
    main()
