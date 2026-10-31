# CLAUDE.md

このリポジトリの規則はすべて AGENTS.md にある。Claude Code も同じ規則に従う。

@AGENTS.md

## Claude Code 固有

- 手順が決まっている作業は Skill を使う: `/new-round` `/preregister` `/report-result` `/record-decision` `/linear-sync` `/handover` `/paper-evidence` `/preview`。
- サブエージェントは `.claude/agents/` の `reader`（読み取り）、`worker`（実装）、`reviewer`（レビュー）を使う。
- 追記専用ファイル（判断ログ、progress）と登録済みプロトコルは `.claude/hooks/` で保護されている。hookに止められたら、迂回せずに追記か新しい版で対応する。
- Linear は `.mcp.json` の `linear` サーバーを使う。つながっていなければ、ユーザーに `/mcp` での認証を頼む。
