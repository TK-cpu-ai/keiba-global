import json
import pathlib
import re
import time
import random
import requests
from bs4 import BeautifulSoup, FeatureNotFound
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================
# 設定
# =====================

START_YEAR = 2024
END_YEAR = 2026

RACE_ID_DIR = pathlib.Path("data/raw/race_id")
OUTPUT_ROOT = pathlib.Path("data/raw/race_result")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://db.netkeiba.com/race/{}/"

WAIT_MIN = 0.8
WAIT_MAX = 1.8
TIMEOUT = 15

PARSER_VERSION = "v5_dbnetkeiba_structured"


# =====================
# session（変更なし）
# =====================
def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update({
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
        ]),
        "Referer": "https://db.netkeiba.com/",
        "Accept-Language": "ja-JP,ja;q=0.9",
    })

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
# util（変更なし）
# =====================
def clean(s):
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip()


def extract_id(href):
    if not href:
        return None
    m = re.search(r"/(\d+)/?$", href)
    return m.group(1) if m else None


def make_soup(html: bytes) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


# ------------------------
# race info（変更なし）
# ------------------------
def parse_race_info(soup, race_id):
    intro = soup.select_one("div.data_intro")
    headline = intro.select_one("h1") if intro else None
    raw_text = clean(intro.get_text(" ", strip=True)) if intro else ""

    def find(p):
        m = re.search(p, raw_text)
        return m.group(1) if m else None

    dist = find(r"(\d{3,4})m")

    return {
        "race_id": race_id,
        "race_name": clean(headline.text) if headline else None,
        "surface": find(r"(芝|ダート)"),
        "distance": int(dist) if dist else None,
        "weather": find(r"天候\s*[:：]\s*(\S+)"),
        "ground_state": find(r"(芝|ダート)\s*[:：]\s*(\S+)"),
        "start_time": find(r"発走\s*[:：]\s*(\d{1,2}:\d{2})"),
        "raw_text": raw_text,
    }


# ------------------------
# horses（変更なし）
# ------------------------
def parse_horses(soup):
    table = soup.select_one("table.race_table_01")
    if not table:
        return []

    header = [clean(th.text) for th in table.select("tr th")]
    rows = table.select("tr")[1:]

    def idx(name):
        return header.index(name) if name in header else None

    horses = []

    for tr in rows:
        td = tr.select("td")
        if not td:
            continue

        def cell(name):
            i = idx(name)
            return clean(td[i].text) if i is not None and i < len(td) else None

        def link(name):
            i = idx(name)
            if i is not None and i < len(td):
                return td[i].select_one("a")
            return None

        horse_a = link("馬名")
        jockey_a = link("騎手")
        trainer_a = link("調教師")
        owner_a = link("馬主")

        horses.append({
            "rank": cell("着順"),
            "frame_no": cell("枠番"),
            "horse_no": cell("馬番"),
            "horse_name": clean(horse_a.text) if horse_a else None,
            "horse_id": extract_id(horse_a["href"]) if horse_a else None,
            "sex_age": cell("性齢"),
            "weight_carried": cell("斤量"),
            "jockey_name": clean(jockey_a.text) if jockey_a else None,
            "jockey_id": extract_id(jockey_a["href"]) if jockey_a else None,
            "time": cell("タイム"),
            "margin": cell("着差"),
            "passing": cell("通過"),
            "last_3f": cell("上り"),
            "odds": cell("単勝"),
            "popularity": cell("人気"),
            "horse_weight": cell("馬体重"),
            "prize": cell("賞金(万円)"),
            "trainer_name": clean(trainer_a.text) if trainer_a else None,
            "trainer_id": extract_id(trainer_a["href"]) if trainer_a else None,
            "owner_name": clean(owner_a.text) if owner_a else None,
            "owner_id": extract_id(owner_a["href"]) if owner_a else None,
        })

    return horses


# ------------------------
# payouts（変更なし）
# ------------------------
def parse_payouts(soup):
    payouts = {}

    for table in soup.select(".pay_table_01"):
        for tr in table.select("tr"):
            cells = [x.get_text("\n").strip() for x in tr.select("th, td")]
            if len(cells) < 3:
                continue

            kind = clean(cells[0])
            nums = cells[1].split("\n")
            yens = cells[2].replace(",", "").split("\n")
            pops = cells[3].split("\n") if len(cells) > 3 else [None] * len(nums)

            payouts[kind] = [
                {
                    "num": clean(nums[i]),
                    "yen": int(yens[i]) if i < len(yens) and yens[i].isdigit() else None,
                    "pop": int(pops[i]) if i < len(pops) and pops[i].isdigit() else None,
                }
                for i in range(len(nums))
            ]

    return payouts


# ------------------------
# extras（変更なし）
# ------------------------
def parse_extras(soup):
    extras = {}
    html = str(soup)

    m = re.search(r"<caption>コーナー通過順位</caption>(.*?)</table>", html, re.S)
    if m:
        table_soup = make_soup(("<table>" + m.group(1) + "</table>").encode())
        extras["corner_passings"] = {
            clean(tr.th.text): clean(tr.td.text)
            for tr in table_soup.select("tr")
            if tr.th and tr.td
        }

    laps = soup.select("td.race_lap_cell")
    if laps:
        extras["lap"] = {
            "lap_raw": clean(laps[0].text),
            "pace_raw": clean(laps[1].text) if len(laps) > 1 else None,
        }

    return extras


# =====================
# main（①②追加）
# =====================
def main():
    session = create_session()

    for year in range(START_YEAR, END_YEAR + 1):

        txt_path = RACE_ID_DIR / f"race_id_{year}.txt"

        if not txt_path.exists():
            print(f"\n=== {year} ===")
            print(f"race_id_{year}.txt が存在しないためスキップ")
            continue

        race_ids = [
            r for r in txt_path.read_text(encoding="utf-8").splitlines()
            if r.isdigit()
        ]

        print(f"\n=== {year} ({len(race_ids)} races) ===")

        out_path = OUTPUT_ROOT / f"race_result_{year}.json"

        # ★ 既存JSON読み込み（差分更新）
        if out_path.exists():
            results = json.loads(out_path.read_text(encoding="utf-8"))
            existing_ids = set(results.keys())
            print(f"既存JSON読み込み: {len(existing_ids)} races")
        else:
            results = {}
            existing_ids = set()

        # ★ 未取得のみ抽出
        target_ids = [r for r in race_ids if r not in existing_ids]

        print(f"新規取得対象: {len(target_ids)} races")

        for i, race_id in enumerate(target_ids, 1):
            url = BASE_URL.format(race_id)

            try:
                resp = session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()

                soup = make_soup(resp.content)

                results[race_id] = {
                    "race": parse_race_info(soup, race_id),
                    "horses": parse_horses(soup),
                    "payouts": parse_payouts(soup),
                    "extras": parse_extras(soup),
                    "meta": {
                        "source": url,
                        "parser_version": PARSER_VERSION,
                    },
                }

                print(f"[{i}/{len(target_ids)}] parsed {race_id}")

            except Exception as e:
                print(f"[ERROR] {race_id}: {e}")

            time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))

        # ★ 保存（既存 + 新規）
        out_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[SAVED] {out_path} ({len(results)} races total)")


if __name__ == "__main__":
    main()
