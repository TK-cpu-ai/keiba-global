from pathlib import Path
from collections import defaultdict
import re

INPUT_DIR = Path("raw_html/race_id")
OUTPUT_DIR = Path("raw_html/race_id_merged")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def merge_race_ids_by_year():
    race_ids_by_year: dict[str, set[str]] = defaultdict(set)
    file_count_by_year: dict[str, int] = defaultdict(int)
    total_lines_by_year: dict[str, int] = defaultdict(int)

    for txt in INPUT_DIR.glob("race_id_*.txt"):
        name = txt.stem  # race_id_YYYYMMDD
        parts = name.split("_")

        if len(parts) != 3:
            continue

        date = parts[2]
        if not (len(date) == 8 and date.isdigit()):
            continue

        year = date[:4]

        lines = txt.read_text(encoding="utf-8").splitlines()
        file_count_by_year[year] += 1
        total_lines_by_year[year] += len(lines)

        for line in lines:
            s = line.strip()
            # 緩やかに数字列を抽出（先頭でなくてもよい）
            m = re.search(r"\d+", s)
            if m:
                race_ids_by_year[year].add(m.group(0))

    # 出力
    for year in sorted(race_ids_by_year.keys()):
        ids = sorted(race_ids_by_year[year])
        out_path = OUTPUT_DIR / f"race_id_{year}.txt"

        out_path.write_text("\n".join(ids), encoding="utf-8")

        print(f"=== {year} ===")
        print(f"source txt files : {file_count_by_year[year]}")
        print(f"raw id lines     : {total_lines_by_year[year]}")
        print(f"unique race_ids  : {len(ids)}")
        print(f"output           : {out_path}")
        print()


if __name__ == "__main__":
    merge_race_ids_by_year()
