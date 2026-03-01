from __future__ import annotations

import argparse
import json
from datetime import datetime

import pandas as pd

from keiba.config.paths import (
    DATASETS_ROOT,
    LEGACY_RACE_RESULT_DIR,
    RAW_RACE_RESULT_DIR,
    ensure_core_dirs,
    make_dataset_version,
)


def to_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return None


def to_float(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_sex_age(sex_age: str | None) -> tuple[str | None, int | None]:
    if not sex_age:
        return None, None
    sex = sex_age[0] if len(sex_age) >= 1 else None
    age = to_int(sex_age[1:]) if len(sex_age) >= 2 else None
    return sex, age


def choose_source_dir():
    if RAW_RACE_RESULT_DIR.exists() and any(RAW_RACE_RESULT_DIR.glob("race_result_*.json")):
        return RAW_RACE_RESULT_DIR
    return LEGACY_RACE_RESULT_DIR


def iter_race_result_files(source_dir, start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        path = source_dir / f"race_result_{year}.json"
        if path.exists():
            yield year, path


def build_rows(start_year: int, end_year: int) -> tuple[list[dict], list[int], str]:
    source_dir = choose_source_dir()
    rows: list[dict] = []
    used_years: list[int] = []

    for year, path in iter_race_result_files(source_dir, start_year, end_year):
        used_years.append(year)
        data = json.loads(path.read_text(encoding="utf-8"))

        for race_id, race_pack in data.items():
            race = race_pack.get("race", {})
            horses = race_pack.get("horses", [])

            for horse in horses:
                sex, age = parse_sex_age(horse.get("sex_age"))
                rank = to_int(horse.get("rank"))

                rows.append(
                    {
                        "race_id": race_id,
                        "year": year,
                        "race_name": race.get("race_name"),
                        "surface": race.get("surface"),
                        "distance": to_int(race.get("distance")),
                        "weather": race.get("weather"),
                        "ground_state": race.get("ground_state"),
                        "start_time": race.get("start_time"),
                        "horse_id": horse.get("horse_id"),
                        "horse_name": horse.get("horse_name"),
                        "frame_no": to_int(horse.get("frame_no")),
                        "horse_no": to_int(horse.get("horse_no")),
                        "rank": rank,
                        "is_win": 1 if rank == 1 else 0,
                        "sex": sex,
                        "age": age,
                        "weight_carried": to_float(horse.get("weight_carried")),
                        "jockey_id": horse.get("jockey_id"),
                        "jockey_name": horse.get("jockey_name"),
                        "trainer_id": horse.get("trainer_id"),
                        "trainer_name": horse.get("trainer_name"),
                        "owner_id": horse.get("owner_id"),
                        "owner_name": horse.get("owner_name"),
                        "odds": to_float(horse.get("odds")),
                        "popularity": to_int(horse.get("popularity")),
                        "last_3f": to_float(horse.get("last_3f")),
                        "time": horse.get("time"),
                        "margin": horse.get("margin"),
                        "horse_weight": horse.get("horse_weight"),
                        "prize": to_float(horse.get("prize")),
                    }
                )

    if not used_years:
        raise FileNotFoundError(
            f"race_result_{{year}}.json not found in {source_dir} for {start_year}-{end_year}"
        )

    return rows, used_years, str(source_dir)


def attach_market_prob(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["market_prob_raw"] = 1.0 / tmp["odds"].where(tmp["odds"] > 0)
    race_sum = tmp.groupby("race_id")["market_prob_raw"].transform("sum")
    tmp["market_prob"] = tmp["market_prob_raw"] / race_sum
    return tmp.drop(columns=["market_prob_raw"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build horse-level dataframe from race_result json.")
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--dataset-version", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_core_dirs()

    rows, used_years, source_dir = build_rows(args.start_year, args.end_year)
    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "No horse rows were created from race_result json. "
            "Check parser output in source json files."
        )

    df = attach_market_prob(df)

    dataset_version = args.dataset_version or make_dataset_version("df")
    out_dir = DATASETS_ROOT / dataset_version
    out_dir.mkdir(parents=True, exist_ok=False)

    data_path = out_dir / "horse_results.pkl"
    meta_path = out_dir / "build_meta.json"

    df.to_pickle(data_path)

    meta = {
        "dataset_version": dataset_version,
        "created_at": datetime.now().isoformat(),
        "source_dir": source_dir,
        "years": used_years,
        "rows": int(len(df)),
        "races": int(df["race_id"].nunique()),
        "columns": list(df.columns),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[SAVED] {data_path}")
    print(f"[SAVED] {meta_path}")
    print(f"rows={meta['rows']}, races={meta['races']}")


if __name__ == "__main__":
    main()
