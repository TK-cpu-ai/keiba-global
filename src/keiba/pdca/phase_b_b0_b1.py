from __future__ import annotations

import argparse
import json
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from pandas.api.types import is_categorical_dtype, is_object_dtype, is_string_dtype

from keiba.config.paths import DATASETS_ROOT, WORKING_ROOT, ensure_core_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase-B B0/B1 experiments.")
    parser.add_argument("--dataset-version", type=str, default="df_v001")
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--report-name", type=str, default=None)
    return parser.parse_args()


def clip_prob(series: pd.Series, eps: float = 1e-6) -> np.ndarray:
    return np.clip(series.astype(float).to_numpy(), eps, 1.0 - eps)


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()

    work = work[work["is_win"].isin([0, 1])].copy()
    work = work[work["year"].notna()].copy()

    work["race_id_int"] = pd.to_numeric(work["race_id"], errors="coerce")
    work = work[work["race_id_int"].notna()].copy()

    work["odds"] = pd.to_numeric(work["odds"], errors="coerce")
    work["market_prob"] = pd.to_numeric(work["market_prob"], errors="coerce")
    work["rank"] = pd.to_numeric(work["rank"], errors="coerce")

    work["field_size"] = work.groupby("race_id")["horse_id"].transform("count")
    fallback_market = 1.0 / work["field_size"].replace(0, np.nan)
    work["market_prob"] = work["market_prob"].fillna(fallback_market)

    safe_odds = work["odds"].where(work["odds"] > 0)
    work["log_odds"] = np.log(safe_odds)
    work["market_rank"] = work.groupby("race_id")["odds"].rank(method="average", ascending=True)

    work = work.sort_values(["horse_id", "race_id_int"]).copy()
    work["avg_finish_last5"] = (
        work.groupby("horse_id")["rank"]
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    )

    work["rel_avg_finish_last5"] = (
        work["avg_finish_last5"]
        - work.groupby("race_id")["avg_finish_last5"].transform("mean")
    )

    work["year"] = work["year"].astype(int)
    return work


def make_pipeline(feature_cols: list[str], df: pd.DataFrame) -> Pipeline:
    categorical_cols = []
    for col in feature_cols:
        if col not in df.columns:
            continue
        series = df[col]
        if is_object_dtype(series) or is_string_dtype(series) or is_categorical_dtype(series):
            categorical_cols.append(col)
    numeric_cols = [col for col in feature_cols if col not in categorical_cols]

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, categorical_cols),
        ]
    )

    model = LogisticRegression(max_iter=200)
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def eval_one_experiment(df: pd.DataFrame, feature_cols: list[str], years: list[int]) -> pd.DataFrame:
    rows = []

    for test_year in years:
        train = df[df["year"] < test_year].copy()
        test = df[df["year"] == test_year].copy()

        if train.empty or test.empty:
            continue

        pipeline = make_pipeline(feature_cols, train)
        pipeline.fit(train[feature_cols], train["is_win"])

        pred_model = pipeline.predict_proba(test[feature_cols])[:, 1]
        pred_market = clip_prob(test["market_prob"])

        y_true = test["is_win"].to_numpy()
        model_ll = float(log_loss(y_true, clip_prob(pd.Series(pred_model))))
        market_ll = float(log_loss(y_true, pred_market))
        model_brier = float(brier_score_loss(y_true, pred_model))
        market_brier = float(brier_score_loss(y_true, pred_market))

        rows.append(
            {
                "year": int(test_year),
                "samples": int(len(test)),
                "races": int(test["race_id"].nunique()),
                "model_logloss": model_ll,
                "market_logloss": market_ll,
                "model_brier": model_brier,
                "market_brier": market_brier,
                "logloss_rel_improve_pct_vs_market": (market_ll - model_ll) / market_ll * 100.0,
            }
        )

    year_df = pd.DataFrame(rows)
    if year_df.empty:
        raise ValueError("No year-level results were produced.")

    total_samples = int(year_df["samples"].sum())
    weighted = {
        "year": "overall",
        "samples": total_samples,
        "races": int(year_df["races"].sum()),
    }

    for col in ["model_logloss", "market_logloss", "model_brier", "market_brier"]:
        weighted[col] = float(np.average(year_df[col], weights=year_df["samples"]))

    weighted["logloss_rel_improve_pct_vs_market"] = (
        (weighted["market_logloss"] - weighted["model_logloss"])
        / weighted["market_logloss"]
        * 100.0
    )

    out = pd.concat([year_df, pd.DataFrame([weighted])], ignore_index=True)
    return out


def compare_b0_b1(b0: pd.DataFrame, b1: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cols = ["year", "model_logloss", "model_brier"]
    merged = b0[cols].merge(b1[cols], on="year", suffixes=("_b0", "_b1"))

    merged["logloss_improve_pct_b1_vs_b0"] = (
        (merged["model_logloss_b0"] - merged["model_logloss_b1"])
        / merged["model_logloss_b0"]
        * 100.0
    )
    merged["brier_delta_b1_minus_b0"] = merged["model_brier_b1"] - merged["model_brier_b0"]

    year_rows = merged[merged["year"] != "overall"].copy()
    overall = merged[merged["year"] == "overall"].iloc[0]

    year_improve_count = int((year_rows["logloss_improve_pct_b1_vs_b0"] > 0).sum())
    year_count = int(len(year_rows))

    decision = {
        "criteria": {
            "overall_logloss_improve_pct_min": 0.5,
            "year_improve_count_min": 2,
            "brier_not_worse": True,
        },
        "actual": {
            "overall_logloss_improve_pct_b1_vs_b0": float(overall["logloss_improve_pct_b1_vs_b0"]),
            "year_improve_count": year_improve_count,
            "year_count": year_count,
            "overall_brier_delta_b1_minus_b0": float(overall["brier_delta_b1_minus_b0"]),
        },
    }

    is_go = (
        decision["actual"]["overall_logloss_improve_pct_b1_vs_b0"] >= 0.5
        and decision["actual"]["year_improve_count"] >= 2
        and decision["actual"]["overall_brier_delta_b1_minus_b0"] <= 0.0
    )
    decision["result"] = "GO_PHASE_C" if is_go else "NO_GO_TRY_B2"

    return merged, decision


def main() -> None:
    args = parse_args()
    ensure_core_dirs()

    ds_dir = DATASETS_ROOT / args.dataset_version
    data_path = ds_dir / "horse_results.pkl"
    if not data_path.exists():
        raise FileNotFoundError(f"dataset not found: {data_path}")

    df = pd.read_pickle(data_path)
    df = prepare_df(df)

    years = list(range(args.start_year, args.end_year + 1))

    feature_base = [
        "market_prob",
        "log_odds",
        "market_rank",
        "surface",
        "distance",
        "frame_no",
        "horse_no",
        "sex",
        "age",
        "weight_carried",
        "popularity",
        "last_3f",
        "field_size",
        "weather",
        "ground_state",
    ]
    feature_b0 = feature_base.copy()
    feature_b1 = feature_base + ["rel_avg_finish_last5"]

    b0_result = eval_one_experiment(df, feature_b0, years)
    b1_result = eval_one_experiment(df, feature_b1, years)
    compare_df, decision = compare_b0_b1(b0_result, b1_result)

    report_name = args.report_name or f"b0_b1_{args.dataset_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = WORKING_ROOT / "reports" / "phase_b" / report_name
    out_dir.mkdir(parents=True, exist_ok=False)

    b0_csv = out_dir / "b0_metrics.csv"
    b1_csv = out_dir / "b1_metrics.csv"
    cmp_csv = out_dir / "b0_b1_compare.csv"
    decision_json = out_dir / "decision.json"

    b0_result.to_csv(b0_csv, index=False)
    b1_result.to_csv(b1_csv, index=False)
    compare_df.to_csv(cmp_csv, index=False)
    decision_json.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[SAVED] {b0_csv}")
    print(f"[SAVED] {b1_csv}")
    print(f"[SAVED] {cmp_csv}")
    print(f"[SAVED] {decision_json}")
    print(f"RESULT={decision['result']}")


if __name__ == "__main__":
    main()
