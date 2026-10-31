---
name: preregister
description: 比較実験を評価データの採点前に登録（事前登録）する。プロトコル文書・機械可読設定・集計スクリプトを書き、smoke test・checkpoint再読込・ハッシュ記録を確認し、独立レビューを通してから判断ログとLinearに記録して凍結する。学習・評価を伴う比較を始める前には必ず使う。「次の実験を登録して」「この比較を回したい」と言われたときに使う。
---

# /preregister

外側の評価データ（outer fold / test set）を1件も採点していない状態で行う。既に採点が始まっていたら、止めてユーザーに報告する。

## 1. 設計を固める（ユーザーと合意する）

docs/protocols/_template.md の各節を埋めるのに必要なことを決める。足りないものだけ質問する。

- 問い、変えるもの1つ、変えないもの、方向仮説
- 対照（新規の同時実行か、保存済み予測か。保存済みなら SHA-256 と再現の記録）
- 分割・seed・採点単位の数・見込みGPU時間
- 主要量1つ、区間の計算法（再標本化の単位、反復、乱数seed）、副次量
- 採用を検討する条件
- checkpoint の保存先と部品

前の実験の結果を見てこの arm を選んだ場合は、それを「限界」に書く。

## 2. ファイルを書く

- `docs/protocols/<id>_protocol.md`（`状態: 下書き`）
- `configs/<id>.yaml`（`registered: false`）
- 集計スクリプト `tools/<id>_report.py`（登録後は変更しない）
- 必要なら学習・評価コードの変更とテスト

コミット: `Draft <id> protocol (ABC-NN, not yet registered)`

## 3. 実行前の確認（全部通るまで登録しない）

1. 関連テストが通る（`project.yaml` の `python.test_command`）。
2. 小さい規模の smoke test が最後まで通る。
3. 集計の検査: 同じ予測を候補と対照の両方に入れて、主要差が 0、区間が [0, 0] になる。被覆（全単位・全seed）の検査も通る。
4. checkpoint: smoke の1単位を保存→再読込→試験推論が同じ出力になる。
   `python3 tools/check_checkpoint.py --checkpoint <path> --loader <module:function> --sample <input>`
5. ハッシュ: `python3 tools/snapshot_sources.py --out results/<id>/run_sources.sha256 configs/<id>.yaml tools/<id>_report.py <コード> <入力>`

## 4. 独立レビュー

`reviewer` サブエージェントに、プロトコル・設定・集計スクリプト・実装の差分を渡し、評価データの混入、seed の混ぜ方、母数、プロトコルと実装の不一致を点検させる。指摘を直してから次へ。

## 5. 登録を確定する

- プロトコルの状態行を `状態: 登録済（YYYY-MM-DD）` にし、設定と集計スクリプトの SHA-256 を書く（このあと hook で追記専用になる）。
- 設定を `registered: true` にする（このあと変更不可）。
- `/record-decision` で判断ログに「<id> を採点前登録」を追記する（決めたこと＝比較・主要量・採用条件・予算、約束すること＝全単位の報告と checkpoint 保存）。
- 台帳の状態を `登録済`、progress に登録の項目（ハッシュ、確認結果、レビューで直した点）を追記。
- Linear: Issue を In Progress にし、コメントに登録文書・判断ログ番号・ハッシュ。

コミット: `Register <id> protocol (decision NNNN, ABC-NN) and its runner`

## 6. 実行の開始（ユーザーの了承を得てから）

予算（単位数・見込み時間・GPU）を示して了承を得る。バックグラウンドで起動し、PID とログの場所を progress と Linear のコメントに書き、台帳を `実行中` にする。途中の精度では止めない・選ばない。
