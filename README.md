# research-harness

AIエージェント（Claude Code / Codex）と一緒に、**後から検証できる研究**を進めるためのテンプレートです。

ブドウ房の多視点計数研究（約3か月、比較実験30件以上、論文投稿まで）で使った進め方を、どのテーマでも使える形に抜き出しました。中身は次のとおりです。

- **ガードレール**: エージェントが必ず読む規則（`CLAUDE.md` / `AGENTS.md`）と、それを機械的に守らせるhook
- **文書の型**: 研究ラウンドの台帳、採点前登録（事前登録）、追記専用の判断ログ、結果報告、論文用の根拠台帳
- **Skills**: 上の型を毎回同じ手順で作る `/new-round` `/preregister` `/record-decision` `/report-result` `/linear-sync` など
- **Linear連携**: 実験1件＝Issue 1件で管理し、Issue・判断ログ・コミットを番号で相互に結ぶ
- **ツール**: 入力やコードのハッシュ記録、checkpointの再読込確認、結果文書の数値照合

## 使い方

### 1. 新しい研究プロジェクトを作る

```bash
mkdir ~/my-research && cd ~/my-research
git clone https://github.com/takahiro-matsumura1231/research-harness.git .
rm -rf .git && git init          # テンプレートの履歴を切り離す
bash scripts/setup.sh            # 対話形式で project.yaml を埋め、hookとエージェント設定を確認
```

GitHubの "Use this template" ボタンで自分のリポジトリを作ってから clone しても構いません。

`setup.sh` が行うこと:

1. `project.yaml`（プロジェクト名、Linearのチーム・プロジェクト、回答言語、Python環境、データ置き場）を対話形式で埋める
2. `.claude/settings.json` のhookが動くかを確かめる
3. Codexを使う場合は、`.codex/agents/*.toml` を `~/.codex/agents/` に入れるかを確認する（既存ファイルは上書きしない）
4. Linear MCPがつながっているかの確認方法を表示する

### 2. Linearをつなぐ

Claude Code はリポジトリ直下の `.mcp.json` で Linear MCP（`https://mcp.linear.app/mcp`）を読み込みます。初回は Claude Code の中で `/mcp` を実行し、`linear` を選んでブラウザでログインしてください。

Codexの場合は `~/.codex/config.toml` に次を追加します。

```toml
[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
```

Linear側では、チームに次のラベルを作っておきます（無くても動きますが、Issueの分類に使います）。

| ラベル | 用途 |
|---|---|
| `Experiment` | 学習・評価・解析 |
| `Writing` | 論文本文・回答書・提出物 |
| `Admin` | 確認・連絡・記録 |
| `Bug` | 実装やデータの不具合 |

運用ルールの詳細は [docs/linear.md](docs/linear.md) にあります。

### 3. 研究を始める

Claude Code を起動して、次のように進めます。

```
/new-round        研究ラウンドを開く（目的、台帳、計画、進捗ログ）
/preregister      実験を採点前に登録する（プロトコル、設定、ハッシュ、判断ログ、Linear Issue）
  … 学習・評価を実行 …
/report-result    登録どおりに集計し、数値を照合して結果文書を書く
/record-decision  判断ログに1件追記する
/linear-sync      Issueの状態と台帳をそろえる
/handover         引き継ぎ文書を最新の状態にする
/paper-evidence   論文の主張を根拠台帳に結びつける
```

Skillを呼ばずに「次の実験を登録して」と頼んでも、エージェントは `CLAUDE.md` の規則に従って同じ手順を踏みます。

## なぜこの形なのか

最初の探索段階では、次の問題が起きました。

- 評価に使う fold でエポックを選んでいた。そのため交差検証の値が楽観的になり、held-out の値と一致しなかった
- 見出しに載せていた数値が、実は5 fold中4 foldだけの平均だった
- 文書には書いてある前処理が、実際には実装されていなかった
- 結果を見てから条件を変えたため、どれが事前の仮説だったか分からなくなった

そこで正式リポジトリでは、規則を5つに絞って強制しました。

1. **選択に評価データを使わない。** モデル選択・ハイパーパラメータ選択は内側の分割だけで行う
2. **結果を見てから変えない。** 変えるなら版を上げ、判断ログに書き、再実行する
3. **推定値・ばらつき・区間を混同しない。** fold SDは区間ではない。アンサンブルの値は単一モデルの性能ではない
4. **判断ログは追記専用。** 過去の項目は書き換えず、後の項目で上書きする
5. **結果文書の数値は照合する。** 手で書き写さず、保存した予測から計算し直して確かめる

加えて、実験のたびに**採点に使った重みそのもの**（前処理・設定・来歴を含む）を保存し、実行前に再読込を確認します。これで、後から「あのモデルをもう一度」と言われても学習し直す必要がありません。

詳しい考え方は [docs/workflow.md](docs/workflow.md) を読んでください。

## ファイル構成

```
CLAUDE.md                  Claude Code が最初に読む規則（AGENTS.md を取り込む）
AGENTS.md                  エージェント共通の規則（Codex もこれを読む）
project.yaml               プロジェクト固有の設定（setup.sh が作る）
.mcp.json                  Linear MCP
.claude/
  settings.json            hook と権限
  hooks/                   追記専用ファイルの保護、登録済みプロトコルの保護
  agents/                  reader / worker / reviewer サブエージェント
  skills/                  /new-round などの手順書
.codex/agents/             Codex 用の reader / worker / reviewer
.agents/skills -> ../.claude/skills   Codex など他のエージェント向けのリンク
docs/
  README.md                文書の索引
  workflow.md              研究の進め方（考え方と手順）
  linear.md                Linear の運用ルール
  handover.md              引き継ぎ文書（随時更新）
  decisions/decision_log.md  追記専用の判断ログ
  rounds/_template/        研究ラウンドの雛形（台帳・計画・進捗）
  protocols/               採点前登録の雛形と登録済みプロトコル
  results/                 結果報告の雛形と結果文書
  paper/                   論文ブリーフ・根拠台帳の雛形
configs/                   機械可読のプロトコル設定（YAML）
tools/
  snapshot_sources.py      実行前に入力・コード・設定の SHA-256 を記録
  check_checkpoint.py      checkpoint の再読込と試験推論を確認
  verify_doc_numbers.py    結果文書の数値を元データと照合
  serve_preview.sh         画像や図をブラウザで見るための簡易サーバー
scripts/setup.sh           初期設定
```

## カスタマイズ

- 規則を追加・変更したいときは `AGENTS.md` を編集し、その理由を判断ログに1件書いてください。
- 機械学習以外の研究（調査、ユーザー実験など）では、`docs/protocols/_template.md` の「分割・乱数」「checkpoint」の節を、その研究で同じ役割を果たすもの（参加者の割付、生データの保存など）に置き換えてください。
- 回答言語は `project.yaml` の `language` で変えられます。

## ライセンス

MIT
