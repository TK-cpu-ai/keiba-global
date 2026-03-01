# データ配置ルール（A/B分離）

このリポジトリは、データを次の2系統で管理します。

- A: 手戻りがほぼない資産（読み取り中心）
- B: 手戻り前提の資産（特徴量変更やモデル更新で再生成）

## A: Immutable（固定資産）

配置先:

- `data/immutable/raw/race_id/`
- `data/immutable/raw/race_result/`
- `data/immutable/masters/`
- `data/immutable/pedigree/`
- `data/immutable/indexes/`

特徴:

- スクレイピング完了後は原則上書きしない
- 追記（新規年の追加）はあり
- モデル改善時も再利用する「ソース・オブ・トゥルース」

## B: Working（作り直し資産）

配置先:

- `data/working/datasets/<dataset_version>/`
- `data/working/experiments/<exp_name>/`

特徴:

- 何度でも再生成する
- `dataset_version` で明確に切り分ける
- 生成物ごとに `build_meta.json` などのメタ情報を残す

## スクリプト配置（責務分離）

- `scripts/scraping/`: 取得・更新系（運用スクリプト）
	- `race_id.py`
	- `race_result.py`
	- `update_masters.py`
	- `fetch_pedigree_5gen.py`
- `scripts/pdca/`: 検証・実験系（PDCA用）
	- `build_dataframe.py`
	- `build_dataframe_v1.ps1`

## 推奨フロー

1. `race_id` を取得（A）
2. `race_result` を取得（A）
3. DataFrame をバージョン付きで構築（B）
4. 特徴量・学習・評価（B）

## 実行コマンド例

```powershell
python scripts/scraping/race_id.py --start-year 2020 --end-year 2026
python scripts/scraping/race_result.py --start-year 2020 --end-year 2026
python scripts/scraping/update_masters.py
python scripts/scraping/fetch_pedigree_5gen.py
python scripts/pdca/build_dataframe.py --start-year 2020 --end-year 2026 --dataset-version df_v001
```

`--dataset-version` 未指定時は、`df_YYYYMMDD_HHMMSS` が自動採番されます。
