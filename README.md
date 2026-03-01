# keiba-local3

競馬データ収集とモデリングのためのローカルワークスペースです。

## ディレクトリ方針（A/B分離）

- A（固定資産）: `data/immutable/`
	- `raw/race_id/`
	- `raw/race_result/`
	- `masters/`
	- `pedigree/`
- B（再生成資産）: `data/working/`
	- `datasets/<dataset_version>/`
	- `experiments/<exp_name>/`

詳細は [docs/data_layout.md](docs/data_layout.md) を参照してください。
PDCA運用は [docs/pdca_playbook.md](docs/pdca_playbook.md) を参照してください。

## セットアップ

```bash
pip install -r requirements.txt
```

## 実行例

```bash
python scripts/scraping/race_id.py --start-year 2020 --end-year 2026
python scripts/scraping/race_result.py --start-year 2020 --end-year 2026
python scripts/scraping/update_masters.py
python scripts/scraping/fetch_pedigree_5gen.py

python scripts/pdca/build_dataframe.py --start-year 2020 --end-year 2026 --dataset-version df_v001
```
