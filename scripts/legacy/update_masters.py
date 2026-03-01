import json
import pathlib
from typing import Dict, Set

# ====================
# project root = this file's parent
# ====================
PROJECT_ROOT = pathlib.Path(__file__).resolve()
while not (PROJECT_ROOT / "raw_json").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent

RAW_JSON_ROOT = PROJECT_ROOT / "raw_json" / "race_result"
DERIVED_ROOT = PROJECT_ROOT / "derived"

MASTERS_DIR = DERIVED_ROOT / "masters"
INDEXES_DIR = DERIVED_ROOT / "indexes"

MASTERS_DIR.mkdir(parents=True, exist_ok=True)
INDEXES_DIR.mkdir(parents=True, exist_ok=True)

SEEN_RACE_IDS_PATH = INDEXES_DIR / "seen_race_ids.json"

HORSES_PATH = MASTERS_DIR / "horses.json"
JOCKEYS_PATH = MASTERS_DIR / "jockeys.json"
TRAINERS_PATH = MASTERS_DIR / "trainers.json"
OWNERS_PATH = MASTERS_DIR / "owners.json"


# ====================
# utils
# ====================
def load_json(path: pathlib.Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: pathlib.Path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def iter_race_json_files():
    if not RAW_JSON_ROOT.exists():
        raise FileNotFoundError(f"raw_json not found: {RAW_JSON_ROOT}")

    for year_dir in sorted(RAW_JSON_ROOT.iterdir()):
        if not year_dir.is_dir():
            continue
        for p in sorted(year_dir.glob("*.json")):
            yield p


# ====================
# master update
# ====================
def upsert_entity(master: Dict, entity_id: str, name: str, race_id: str):
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


# ====================
# main
# ====================
def main():
    seen_race_ids: Set[str] = set(load_json(SEEN_RACE_IDS_PATH, []))

    horses_master = load_json(HORSES_PATH, {})
    jockeys_master = load_json(JOCKEYS_PATH, {})
    trainers_master = load_json(TRAINERS_PATH, {})
    owners_master = load_json(OWNERS_PATH, {})

    processed = 0

    for race_json_path in iter_race_json_files():
        data = load_json(race_json_path, {})
        race = data.get("race", {})
        race_id = race.get("race_id")

        if not race_id or race_id in seen_race_ids:
            continue

        for h in data.get("horses", []):
            upsert_entity(
                horses_master,
                h.get("horse_id"),
                h.get("horse_name"),
                race_id,
            )
            upsert_entity(
                jockeys_master,
                h.get("jockey_id"),
                h.get("jockey_name"),
                race_id,
            )
            upsert_entity(
                trainers_master,
                h.get("trainer_id"),
                h.get("trainer_name"),
                race_id,
            )
            upsert_entity(
                owners_master,
                h.get("owner_id"),
                h.get("owner_name"),
                race_id,
            )

        seen_race_ids.add(race_id)
        processed += 1

    save_json(HORSES_PATH, horses_master)
    save_json(JOCKEYS_PATH, jockeys_master)
    save_json(TRAINERS_PATH, trainers_master)
    save_json(OWNERS_PATH, owners_master)
    save_json(SEEN_RACE_IDS_PATH, sorted(seen_race_ids))

    print(f"update_masters finished. new races processed: {processed}")


if __name__ == "__main__":
    main()
