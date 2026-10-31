---
name: report-result
description: 登録済みの実験が終わった後、登録どおりの集計スクリプトで主要量・副次量を出し、被覆とハッシュを確認し、数値を照合して結果文書を書く。台帳・progress・Linearを更新する。「結果をまとめて」「実験が終わった」と言われたときに使う。
---

# /report-result

## 1. 終わったことを確かめる

- 全採点単位（seed × fold × arm）について、予測・manifest・checkpoint があるか数える。欠けがあれば、結果を書く前に報告する。
- 学習ログにエラーがないか。
- `results/<id>/run_sources.sha256` のハッシュが現在のファイルと一致するか（`python3 tools/snapshot_sources.py --check results/<id>/run_sources.sha256`）。一致しなければ、何が変わったかを特定して報告する。

## 2. 登録どおりに集計する

- 登録した `tools/<id>_report.py` だけを使う。集計を変えたくなったら、それは登録の変更なので、新しい版として別に扱い、登録版の結果も残す。
- 出力は `results/<id>/` に置く（summary.json など、文書から参照できる形）。

## 3. 結果文書を書く

`docs/results/_template.md` をもとに `docs/results/<id>_result.md` を作る。

- 主要結果を先に書き、採用を検討する条件を満たしたかを明記する。満たさなかった場合も同じ詳しさで書く。
- 推定値・seed/fold のばらつき・区間を分ける。アンサンブルを単一モデルの性能と書かない。
- 副次量は探索的と書く。小さい部分集団から機序を断定しない。
- 「示すこと / 示さないこと」を書く。

## 4. 数値を照合する

文書の数値に照合用の注釈を付け、照合する:

```markdown
MAE は 2.2941<!-- verify: results/<id>/summary.json:arms.candidate.mae round=4 -->
```

```bash
python3 tools/verify_doc_numbers.py docs/results/<id>_result.md
```

全て一致するまで直す。サブエージェントに数値を抜き出させた場合も、ここで元ファイルと照合されることを確認する。

## 5. 記録

- 台帳を `完了`（または `分析中`）にし、証拠のリンクを入れる。
- progress に結果の項目（実行、主要結果、副次結果、限界、証拠、次）を追記する。
- Linear: コメントに主要結果の1行と文書へのリンク。完了なら Done。
- 採否や標準モデルの変更など判断があれば `/record-decision`。
- コミット: `<id>: registered result (decision NNNN, ABC-NN)`

ユーザーへの報告は、主要結果1行 → 条件の成否 → 注意点 → 次の判断の候補、の順に短く。
