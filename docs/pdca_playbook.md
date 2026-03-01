# 競馬予想PDCA運用ガイド（ROI 110%以上を目標）

このドキュメントは、回収率改善を再現可能に進めるための実務手順を定義します。

## 0. 方針

- 目標: OOS（将来データ）で ROI 1.10 以上
- 原則: `確率品質 → 校正 → ベット戦略` の順で進める
- 運用: 1回で完成させず、短いサイクルで継続改善する

## 1. フェーズ構成

### Phase A: データ基盤（品質・再現性）

目的:

- 同じ入力から同じデータセットを再生成できる状態を固定

主作業:

- immutable（A）とworking（B）の分離維持
- `data/working/datasets/<dataset_version>/` にデータセット化
- `build_meta.json` に入力年・行数・列を記録

評価項目:

- 欠損率・重複・型不一致
- `race_id` 単位での整合（異常なodds・重複行など）

Go/No-Go:

- Go: 再生成一致・主要品質チェック通過
- No-Go: 欠損や整合異常を残したまま次フェーズへ進まない

### Phase B: 確率モデル（LogLoss最適化）

目的:

- 市場確率より良い確率予測を作る

主作業:

- 最小構成特徴量から開始（市場特徴 + 差分特徴1本）
- 年次ウォークフォワードで学習/評価

評価項目:

- モデルLogLoss vs 市場LogLoss（年別・全体）
- Brier Score

Go/No-Go:

- Go: 全体で市場比 LogLoss 改善（目安 0.5%〜1.0%以上）
- No-Go: 改善が単年依存・または市場未満

### Phase C: キャリブレーション

目的:

- 予測確率の過信/過小を補正する

主作業:

- Isotonic / Platt を比較
- OOFで学習しテスト年へ適用

評価項目:

- Calibration curve
- ECE（Expected Calibration Error）
- キャリブ前後LogLoss

Go/No-Go:

- Go: ECE改善かつLogLoss悪化なし
- No-Go: ECE悪化またはLogLoss悪化

### Phase D: ベット戦略（ROI最適化）

目的:

- 確率優位を収益へ変換する

主作業:

- edge閾値・オッズ帯・選択ルールを比較
- 固定額 → Fractional Kelly の順に評価

評価項目:

- ROI
- Max Drawdown
- ベット件数
- 年別安定性

Go/No-Go:

- Go: OOS ROI >= 1.10 かつ過度な単年依存なし
- No-Go: ROI未達、またはDD過大

### Phase E: 安定運用

目的:

- 月次運用での劣化検知とロールバック可能性を担保

主作業:

- 月次監視（ROI・LogLoss・ECE）
- 閾値超過時の停止/再学習ルール

評価項目:

- 期間別の指標安定性
- ドリフト検知結果

Go/No-Go:

- Go: 観測期間で安定
- No-Go: 劣化時はPhase Bへ戻る

## 2. 実務ルール（ゲート制）

- Phase B未通過で Phase Dに進まない
- Phase C未通過で Phase Dに進まない
- ROI施策は、確率品質を壊す変更より優先しない

## 3. 1サイクルの実行単位

1. DataFrame版更新（例: `df_v001` → `df_v002`）
2. 特徴量変更は最小1〜2点に限定
3. B/C/D評価を同一期間で実施
4. レポート化して採否判定

## 4. 最初の推奨スタート

最初は次の最小構成で開始する:

- `market_prob`
- `log_odds`
- `market_rank`
- `rel_past_win_rate`

この構成で Phase B を最初に通すことを最優先とする。
