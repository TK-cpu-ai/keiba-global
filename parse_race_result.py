from bs4 import BeautifulSoup
import re
import csv

HTML_PATH = "raw_html\race_result_html\2019\201901010101.html"
OUTPUT_CSV = "output/race_201901010101_results.csv"


def load_html(path):
    # netkeibaはEUC-JP
    with open(path, "r", encoding="euc-jp", errors="strict") as f:
        html = f.read()

    return BeautifulSoup(html, "html.parser")


def parse_race_info(soup):
    info = {}

    info["race_name"] = soup.find("h1").get_text(strip=True)

    summary = soup.select_one("div.data_intro")
    text = summary.get_text(" ", strip=True)

    m = re.search(r"(芝|ダ)(\d+)m", text)
    if m:
        info["surface"] = m.group(1)
        info["distance"] = int(m.group(2))

    m = re.search(r"天候\s*:\s*(\S+)", text)
    if m:
        info["weather"] = m.group(1)

    m = re.search(r"馬場\s*:\s*(\S+)", text)
    if m:
        info["ground_state"] = m.group(1)

    return info


def parse_horse_results(soup):
    results = []

    table = (
        soup.select_one("table.race_table_01")
        or soup.select_one("table#All_Result_Table")
        or soup.select_one("table.race_table_old")
    )

    if table is None:
        raise RuntimeError("レース結果テーブルが見つかりません")

    rows = table.select("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 15:
            continue  # ヘッダ行など

        result = {
            "rank": cols[0].get_text(strip=True),
            "frame": cols[1].get_text(strip=True),
            "horse_no": cols[2].get_text(strip=True),
            "horse_name": cols[3].get_text(strip=True),
            "sex_age": cols[4].get_text(strip=True),
            "weight": cols[5].get_text(strip=True),
            "jockey": cols[6].get_text(strip=True),
            "time": cols[7].get_text(strip=True),
            "margin": cols[8].get_text(strip=True),
            "last_3f": cols[11].get_text(strip=True),
            "odds": cols[12].get_text(strip=True),
            "popularity": cols[13].get_text(strip=True),
            "horse_weight": cols[14].get_text(strip=True),
        }

        horse_link = cols[3].find("a")
        if horse_link:
            result["horse_id"] = horse_link["href"].split("/")[-2]

        jockey_link = cols[6].find("a")
        if jockey_link:
            result["jockey_id"] = jockey_link["href"].split("/")[-2]

        results.append(result)

    return results



def main():
    soup = load_html(HTML_PATH)

    race_info = parse_race_info(soup)
    horse_results = parse_horse_results(soup)

    if not horse_results:
        raise RuntimeError("馬データが1件も取得できませんでした")


    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=horse_results[0].keys())
        writer.writeheader()
        writer.writerows(horse_results)

    print("[DONE]", OUTPUT_CSV)


if __name__ == "__main__":
    main()
