---
name: preview
description: 生成した画像・図・HTMLをユーザーにブラウザで見せる。tools/serve_preview.sh でローカルHTTPサーバーを起動し、複数画像なら一覧ページを作ってURLを示す。図やモンタージュを作ったとき、ユーザーが「見せて」と言ったときに使う。ファイルパスだけを渡して終わらない。
---

# /preview

1. 見せたいファイルを1つのディレクトリにまとめる（例: `results/<id>/preview/`）。
2. 画像が複数あるときは `index.html` を作る（横幅いっぱいに並べ、各画像の下にファイル名と説明）。
3. サーバーを起動する（既に起動していれば再利用される）:
   ```bash
   bash tools/serve_preview.sh <ディレクトリ>
   ```
   ポートは project.yaml の `preview.port`（既定 8765）。127.0.0.1 にだけ bind する。
4. `http://localhost:<port>/<path>` のリンクを示す。SSH 越しなら、ユーザーの手元で `ssh -L <port>:localhost:<port> <server>` が必要だと一度伝える。
