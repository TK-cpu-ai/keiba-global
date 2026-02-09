import time
import random
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================
# 設定
# =====================
INPUT_DIR = Path("raw_html/race_id_merged")
OUTPUT_DIR = Path("raw_html/race_result_html")

BASE_URL = "https://db.netkeiba.com/race/{}/"

WAIT_MIN = 0.8
WAIT_MAX = 1.8
TIMEOUT = 15

# テスト実行用設定: True にすると各年で先頭 N 件だけダウンロードします
TEST_MODE = False
TEST_LIMIT = 3

# =====================
# Session 構築
# =====================
def create_session() -> requests.Session:
    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://db.netkeiba.com/",
        "Accept-Language": "ja-JP,ja;q=0.9",
    }
    session.headers.update(headers)

    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

# =====================
# race_id 読み込み
# =====================
def load_race_ids(txt_path: Path) -> list[str]:
    return [
        line.strip()
        for line in txt_path.read_text(encoding="utf-8").splitlines()
        if line.strip().isdigit()
    ]

# =====================
# メイン処理
# =====================
def main():
    session = create_session()

    year_files = sorted(INPUT_DIR.glob("race_id_*.txt"))

    for txt in year_files:
        year = txt.stem.split("_")[-1]
        race_ids = load_race_ids(txt)

        print(f"\n=== {year} ===")
        print(f"target races : {len(race_ids)}")

        out_dir = OUTPUT_DIR / year
        out_dir.mkdir(parents=True, exist_ok=True)

        # テストモードなら先頭 N 件のみに制限
        if TEST_MODE and TEST_LIMIT > 0:
            race_ids = race_ids[:TEST_LIMIT]

        for i, race_id in enumerate(race_ids, 1):
            out_file = out_dir / f"{race_id}.html"
            if out_file.exists():
                continue

            url = BASE_URL.format(race_id)

            try:
                resp = session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()

                out_file.write_bytes(resp.content)
                print(f"[{i}/{len(race_ids)}] saved {race_id}")

            except Exception as e:
                print(f"[ERROR] {race_id} : {e}")

            time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))

    print("\n[DONE] db.netkeiba.com download finished")

if __name__ == "__main__":
    main()
