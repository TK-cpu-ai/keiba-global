import json
import pathlib
import re
from bs4 import BeautifulSoup, FeatureNotFound

INPUT_ROOT = pathlib.Path("raw_html/race_result_html")
OUTPUT_ROOT = pathlib.Path("raw_json/race_result")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

PARSER_VERSION = "v5_dbnetkeiba_structured"


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
# race info
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
# horses（ヘッダベース・賞金対応）
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
                a = td[i].select_one("a")
                return a
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
# payouts（完全構造化）
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

            records = []
            for i in range(len(nums)):
                records.append({
                    "num": clean(nums[i]),
                    "yen": int(yens[i]) if i < len(yens) and yens[i].isdigit() else None,
                    "pop": int(pops[i]) if i < len(pops) and pops[i].isdigit() else None,
                })

            payouts[kind] = records

    return payouts



# ------------------------
# extras（corner + lap 完全安定版）
# ------------------------
def parse_extras(soup):
    extras = {}

    html = str(soup)

    # ========================
    # コーナー通過順位
    # ========================
    corner = {}

    m = re.search(
        r"<caption>コーナー通過順位</caption>(.*?)</table>",
        html,
        re.S
    )

    if m:
        table_html = "<table>" + m.group(1) + "</table>"
        table_soup = make_soup(table_html.encode("utf-8"))

        for tr in table_soup.select("tr"):
            th = tr.select_one("th")
            td = tr.select_one("td")
            if not th or not td:
                continue

            key = clean(th.text)
            val = clean(td.text)

            corner[key] = val

    if corner:
        extras["corner_passings"] = corner

    # ========================
    # ラップタイム / ペース
    # ========================
    laps = soup.select("td.race_lap_cell")
    if laps:
        lap_info = {}
        lap_info["lap_raw"] = clean(laps[0].text)
        if len(laps) > 1:
            lap_info["pace_raw"] = clean(laps[1].text)

        extras["lap"] = lap_info

    return extras




def parse_file(html_path):
    soup = make_soup(html_path.read_bytes())
    race_id = html_path.stem

    return {
        "race": parse_race_info(soup, race_id),
        "horses": parse_horses(soup),
        "payouts": parse_payouts(soup),
        "extras": parse_extras(soup),
        "meta": {
            "source": str(html_path),
            "parser_version": PARSER_VERSION,
        },
    }


def main():
    for year_dir in INPUT_ROOT.iterdir():
        if not year_dir.is_dir():
            continue

        out_dir = OUTPUT_ROOT / year_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)

        for html in year_dir.glob("*.html"):
            data = parse_file(html)
            out = out_dir / f"{html.stem}.json"
            out.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )


if __name__ == "__main__":
    main()
