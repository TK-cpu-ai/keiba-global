from __future__ import annotations

from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_ROOT = PROJECT_ROOT / "data"

# A: 手戻りが少ない資産（読み取り中心）
IMMUTABLE_ROOT = DATA_ROOT / "immutable"
RAW_ROOT = IMMUTABLE_ROOT / "raw"
RAW_RACE_ID_DIR = RAW_ROOT / "race_id"
RAW_RACE_RESULT_DIR = RAW_ROOT / "race_result"
IMMUTABLE_MASTERS_DIR = IMMUTABLE_ROOT / "masters"
IMMUTABLE_PEDIGREE_DIR = IMMUTABLE_ROOT / "pedigree"
IMMUTABLE_INDEXES_DIR = IMMUTABLE_ROOT / "indexes"

# B: 手戻りが多い資産（何度も再生成）
WORKING_ROOT = DATA_ROOT / "working"
DATASETS_ROOT = WORKING_ROOT / "datasets"
EXPERIMENTS_ROOT = WORKING_ROOT / "experiments"

# 既存資産の互換読み取り用
LEGACY_RAW_ROOT = DATA_ROOT / "raw"
LEGACY_RACE_ID_DIR = LEGACY_RAW_ROOT / "race_id"
LEGACY_RACE_RESULT_DIR = LEGACY_RAW_ROOT / "race_result"


def ensure_core_dirs() -> None:
    RAW_RACE_ID_DIR.mkdir(parents=True, exist_ok=True)
    RAW_RACE_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    IMMUTABLE_MASTERS_DIR.mkdir(parents=True, exist_ok=True)
    IMMUTABLE_PEDIGREE_DIR.mkdir(parents=True, exist_ok=True)
    IMMUTABLE_INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    DATASETS_ROOT.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_ROOT.mkdir(parents=True, exist_ok=True)


def make_dataset_version(prefix: str = "ds") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}"
