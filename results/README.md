# results/

登録済み実験の生成物を `results/<id>/` に置く。gitに入れるのは、再計算できる小さな表・予測・集計（summary.json、predictions.tsv.gz など）、manifest、`run_sources.sha256`。checkpoint や大きなキャッシュは `project.yaml` の `paths` に置き、manifest からパスと SHA-256 で参照する。

元の実験結果は移動・上書きしない。後から作る派生物（論文の図表など）は別のディレクトリ（`results/paper/` など）に出す。
