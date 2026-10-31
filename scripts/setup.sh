#!/usr/bin/env bash
# Initial setup for a project created from auto-research.
#   bash scripts/setup.sh           interactive
#   bash scripts/setup.sh --check   only run the checks
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
check_only=false
[[ "${1:-}" == "--check" ]] && check_only=true

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }

ask() {  # ask KEY "prompt" default  -> replaces the first `KEY: "TODO..."` / `KEY: TODO` in project.yaml
  local key="$1" prompt="$2" def="${3:-}" val
  read -r -p "  $prompt${def:+ [$def]}: " val || true
  val="${val:-$def}"
  [[ -z "$val" ]] && return
  python3 - "$key" "$val" <<'PY'
import re, sys
key, val = sys.argv[1], sys.argv[2]
p = "project.yaml"
s = open(p, encoding="utf-8").read()
pat = re.compile(rf'^(\s*{re.escape(key)}:\s*)"?TODO[^"\n]*"?', re.M)
s, n = pat.subn(lambda m: f'{m.group(1)}"{val}"', s, count=1)
open(p, "w", encoding="utf-8").write(s)
PY
}

if ! $check_only; then
  say "1. project.yaml を埋めます（Enter で既定値、空欄はあとで手で編集）"
  ask name "プロジェクト名" "$(basename "$root")"
  ask one_line "研究の問いを1文で"
  ask owner "担当者" "$(git config user.name 2>/dev/null || true)"
  ask started "開始日" "$(date +%F)"
  ask team_key "Linear チームキー（Issue番号の接頭辞、例 RSC）"
  ask project "Linear プロジェクト名"
  ask raw_data "原データの場所（git外）"
  ask checkpoints "checkpoint の保存先（git外）"
  ask cache "キャッシュの場所（git外）"
  ask gpus "GPU（例: RTX 4090 x2）"
  read -r -p "  Python インタプリタ [python]: " py || true
  if [[ -n "${py:-}" ]]; then
    python3 - "$py" <<'PY'
import re, sys
p = "project.yaml"; s = open(p, encoding="utf-8").read()
s = re.sub(r'^(\s*interpreter:\s*)\S+', lambda m: m.group(1) + sys.argv[1], s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s)
PY
  fi
  today="$(date +%F)"
  sed -i "s/^## 0001 — TODO — /## 0001 — $today — /" docs/decisions/decision_log.md
  sed -i "s/^最終更新: TODO（YYYY-MM-DD）/最終更新: $today/" docs/handover.md
fi

say "2. 確認"
command -v python3 >/dev/null && ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)" || warn "python3 がありません（hook に必要）"
command -v claude >/dev/null && ok "Claude Code $(claude --version 2>/dev/null | head -1)" || warn "Claude Code が見つかりません: https://docs.claude.com/claude-code"
command -v codex >/dev/null && ok "Codex CLI あり" || warn "Codex CLI なし（使わないなら問題なし）"
command -v tmux >/dev/null && ok "tmux あり" || warn "tmux なし（serve_preview.sh は nohup で動きます）"

# hook self-test: an edit that rewrites the decision log must be blocked
tmp_in='{"tool_name":"Edit","tool_input":{"file_path":"docs/decisions/decision_log.md","old_string":"# Decision log","new_string":"# Changed"}}'
if echo "$tmp_in" | CLAUDE_PROJECT_DIR="$root" python3 .claude/hooks/guard_records.py 2>/dev/null; then
  warn "hook が書き換えを止めませんでした。.claude/hooks/guard_records.py を確認してください"
else
  ok "追記専用 hook が動作"
fi
if grep -q TODO project.yaml; then warn "project.yaml に TODO が残っています: $(grep -c TODO project.yaml) 箇所"; else ok "project.yaml 記入済み"; fi

if ! $check_only && [[ -d .codex/agents ]]; then
  say "3. Codex のサブエージェント（reader / worker / reviewer）"
  read -r -p "  ~/.codex/agents/ にコピーしますか？既存ファイルは上書きしません [y/N]: " yn || true
  if [[ "${yn:-}" =~ ^[Yy]$ ]]; then
    mkdir -p ~/.codex/agents
    for f in .codex/agents/*.toml; do
      dest=~/.codex/agents/"$(basename "$f")"
      if [[ -e "$dest" ]]; then warn "既存のためスキップ: $dest"; else cp "$f" "$dest"; ok "コピー: $dest"; fi
    done
  fi
  if [[ -f ~/.codex/config.toml ]] && ! grep -q 'mcp_servers.linear' ~/.codex/config.toml; then
    warn "Codex で Linear を使うなら ~/.codex/config.toml に追加してください:"
    printf '      [mcp_servers.linear]\n      url = "https://mcp.linear.app/mcp"\n'
  fi
fi

say "4. 次にやること"
cat <<'TXT'
  - claude を起動し、/mcp で linear を認証する
  - docs/decisions/decision_log.md の 0001 の TODO を埋める（探索段階があれば、そのタグと持ち込むもの）
  - /new-round で最初の研究ラウンドを開く
  - 最初のコミット:  git add -A && git commit -m "Open repository from auto-research"
TXT
