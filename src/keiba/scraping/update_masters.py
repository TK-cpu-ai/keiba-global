from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from keiba.config.paths import (
    IMMUTABLE_INDEXES_DIR,
    IMMUTABLE_MASTERS_DIR,
    LEGACY_RACE_RESULT_DIR,
    RAW_RACE_RESULT_DIR,
    ensure_core_dirs,
)


SEEN_RACE_IDS_PATH = IMMUTABLE_INDEXES_DIR / "seen_race_ids.json"

HORSES_PATH = IMMUTABLE_MASTERS_DIR / "horses.json"
JOCKEYS_PATH = IMMUTABLE_MASTERS_DIR / "jockeys.json"
TRAINERS_PATH = IMMUTABLE_MASTERS_DIR / "trainers.json"
OWNERS_PATH = IMMUTABLE_MASTERS_DIR / "owners.json"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_source_dir() -> Path:
    if RAW_RACE_RESULT_DIR.exists() and any(RAW_RACE_RESULT_DIR.glob("race_result_*.json")):
        return RAW_RACE_RESULT_DIR
    return LEGACY_RACE_RESULT_DIR


def iter_race_json_files():
    source_dir = choose_source_dir()
    if not source_dir.exists():
        raise FileNotFoundError(f"race_result dir not found: {source_dir}")

    for path in sorted(source_dir.glob("race_result_*.json")):
        yield path


def upsert_entity(master: Dict, entity_id: str, name: str, race_id: str) -> None:
    if not entity_id:
        return

    if entity_id not in master:
        master[entity_id] = {
            "id": entity_id,
            "name": name,
            "first_seen_race": race_id,
            "last_seen_race": race_id,
        }
    else:
        master[entity_id]["last_seen_race"] = race_id


def main() -> None:
    ensure_core_dirs()

    seen_race_ids = set(load_json(SEEN_RACE_IDS_PATH, []))

    horses_master = load_json(HORSES_PATH, {})
    jockeys_master = load_json(JOCKEYS_PATH, {})
    trainers_master = load_json(TRAINERS_PATH, {})
    owners_master = load_json(OWNERS_PATH, {})

    processed = 0
    source_dir = choose_source_dir()

    for race_json_path in iter_race_json_files():
        yearly_data = load_json(race_json_path, {})

        for race_id, race_pack in yearly_data.items():
            if race_id in seen_race_ids:
                continue

            for horse in race_pack.get("horses", []):
                upsert_entity(horses_master, horse.get("horse_id"), horse.get("horse_name"), race_id)
                upsert_entity(jockeys_master, horse.get("jockey_id"), horse.get("jockey_name"), race_id)
                upsert_entity(trainers_master, horse.get("trainer_id"), horse.get("trainer_name"), race_id)
                upsert_entity(owners_master, horse.get("owner_id"), horse.get("owner_name"), race_id)

            seen_race_ids.add(race_id)
            processed += 1

    save_json(HORSES_PATH, horses_master)
    save_json(JOCKEYS_PATH, jockeys_master)
    save_json(TRAINERS_PATH, trainers_master)
    save_json(OWNERS_PATH, owners_master)
    save_json(SEEN_RACE_IDS_PATH, sorted(seen_race_ids))

    print(f"source={source_dir}")
    print(f"update_masters finished. new races processed: {processed}")


if __name__ == "__main__":
    main()
