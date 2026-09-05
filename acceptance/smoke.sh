#!/usr/bin/env bash
# acceptance/smoke.sh — LLM を使わずに縦断ユースケース（2 日分）を再現する受入スクリプト（v2）。
# 使い方: リポジトリルートで `bash acceptance/smoke.sh`。すべて PASS で exit 0。
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX=(python3 "$ROOT/plugins/kiseki-da/core/ctx/cli.py")
FX="$ROOT/acceptance/fixtures"
export KISEKI_DA_HOME="$(mktemp -d)"
WS="$(mktemp -d)"            # 作業ディレクトリは KISEKI_DA_HOME の外（KISEKI_DA_HOME 配下の書込は deny されるため）
TMP="$(mktemp -d)"
trap 'rm -rf "$KISEKI_DA_HOME" "$WS" "$TMP"' EXIT
FAIL=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=1; }

# hook <event> <fixture>: サブシェルを使わず、親シェルの HOOK_OUT / HOOK_RC / HOOK_MS に結果を入れる。時間計測は python3（macOS の date に %N が無いため）。
# fixtures の __FX__（fixtures ディレクトリ）と __CWD__（作業ディレクトリ）を置換してから渡す。
hook() {
  local t0 t1
  sed -e "s#__FX__#$FX#g" -e "s#__CWD__#$WS#g" "$2" > "$TMP/payload.json"
  t0=$(python3 -c 'import time;print(int(time.time()*1000))')
  "${CTX[@]}" hook "$1" --env claude-code < "$TMP/payload.json" > "$TMP/out" 2> "$TMP/err"
  HOOK_RC=$?
  t1=$(python3 -c 'import time;print(int(time.time()*1000))')
  HOOK_OUT="$(cat "$TMP/out")"
  HOOK_MS=$(( t1 - t0 ))
  [ "$HOOK_MS" -lt 300 ] || fail "C10 hook $1 took ${HOOK_MS}ms (>= 300ms)"
}
sid2() { sed 's/"s-demo-1"/"s-demo-2"/g' "$1" > "$TMP/sid2.json"; echo "$TMP/sid2.json"; }

echo "== Day 1 =="
"${CTX[@]}" init >/dev/null && pass "C1a init" || fail "C1a init"

hook session-start "$FX/cc-session-start.json"
[ $HOOK_RC -eq 0 ] && [ -n "$HOOK_OUT" ] && pass "C1b session-start emits context (${HOOK_MS}ms)" || fail "C1b session-start rc=$HOOK_RC"
echo "$HOOK_OUT" | grep -q "session: s-demo-1" && pass "C1b2 context shows session id" || fail "C1b2 session id line missing"
TOK=$("${CTX[@]}" build --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["manifest"]["used"])')
[ "$TOK" -le 2500 ] && pass "C1c build tokens=$TOK <= 2500" || fail "C1c build tokens=$TOK"
grep -q '"type": *"context_manifest"' "$KISEKI_DA_HOME/events.jsonl" && pass "C1d context_manifest logged" || fail "C1d context_manifest"

"${CTX[@]}" task new --goal "認証トークンの自動更新を追加する" --risk R1 --kind code --id demo-auth >/dev/null && pass "C2a task new" || fail "C2a task new"
"${CTX[@]}" task set demo-auth --add-criterion "更新処理の単体テストが通る :: pytest tests/test_auth.py -q" >/dev/null || fail "C2b add C1"
"${CTX[@]}" task set demo-auth --add-criterion "変更差分を読み返した :: Read $WS/repo/git-diff.txt" >/dev/null || fail "C2c add C2"
"${CTX[@]}" task close demo-auth > "$TMP/close1" 2>&1; RC=$?
[ $RC -eq 1 ] && grep -q "C1" "$TMP/close1" && pass "C2d close refused without evidence (lists C1)" || fail "C2d close should be refused with a list, rc=$RC"

hook post-tool "$FX/cc-post-tool-pytest.json"
[ $HOOK_RC -eq 0 ] && [ -z "$HOOK_OUT" ] && pass "C3a post-tool pytest logged, no output (${HOOK_MS}ms)" || fail "C3a post-tool rc=$HOOK_RC out='$HOOK_OUT'"
"${CTX[@]}" task set demo-auth --evidence C1=last >/dev/null && pass "C3b evidence C1=last" || fail "C3b evidence C1"
hook post-tool "$FX/cc-post-tool-read.json"
"${CTX[@]}" task set demo-auth --evidence C2=last >/dev/null && pass "C3c evidence C2=last" || fail "C3c evidence C2"

hook stop "$FX/cc-stop.json"
echo "$HOOK_OUT" | grep -q '"decision": *"block"' && pass "C4a stop blocks once for open R1 card (${HOOK_MS}ms)" || fail "C4a stop should block: '$HOOK_OUT'"
hook stop "$FX/cc-stop.json"
[ -z "$HOOK_OUT" ] && pass "C4b second stop emits nothing" || fail "C4b second stop emitted: '$HOOK_OUT'"

"${CTX[@]}" task close demo-auth >/dev/null && pass "C3d close succeeds with evidence" || fail "C3d close with evidence"

hook session-end "$FX/cc-session-end.json"
[ $HOOK_RC -eq 0 ] && pass "C5a session-end ok (${HOOK_MS}ms)" || fail "C5a session-end rc=$HOOK_RC"
N=$("${CTX[@]}" candidate list --status pending --json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$N" -eq 1 ] && pass "C5b one candidate from transcript" || fail "C5b candidates=$N"

echo "== Day 2 =="
hook session-start "$(sid2 "$FX/cc-session-start.json")"
echo "$HOOK_OUT" | grep -q "未承認候補 1 件" && pass "C6a build mentions pending candidate" || fail "C6a pending candidate not shown"
CID=$("${CTX[@]}" candidate list --status pending --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
python3 -c 'import json,sys; print(json.dumps({"session_id":"s-demo-2","hook_event_name":"UserPromptSubmit","cwd":sys.argv[1],"prompt":"この記憶候補を承認して"}))' "$WS/repo" > "$TMP/user-input.json"
hook user-input "$TMP/user-input.json"
"${CTX[@]}" approve "$CID" --quote "この記憶候補を承認して" --review-by 2027-03-01 >/dev/null && pass "C6b approve $CID" || fail "C6b approve"
"${CTX[@]}" build | grep -q "ISO 8601" && pass "C6c approved preference is resident" || fail "C6c preference missing from build"
"${CTX[@]}" search "ISO 8601" | grep -q "\[profile\]" && pass "C7 search hits profile" || fail "C7 search"

echo "== Guards =="
hook pre-tool "$FX/cc-pre-tool-rm.json";     echo "$HOOK_OUT" | grep -q '"deny"' && pass "C8a deny rm -rf /" || fail "C8a rm: '$HOOK_OUT'"
hook pre-tool "$FX/cc-pre-tool-push.json";   echo "$HOOK_OUT" | grep -q '"deny"' && pass "C8b deny force push" || fail "C8b push: '$HOOK_OUT'"
hook pre-tool "$FX/cc-pre-tool-deploy.json"; echo "$HOOK_OUT" | grep -q '"ask"'  && pass "C8c ask deploy" || fail "C8c deploy: '$HOOK_OUT'"
hook pre-tool "$FX/cc-pre-tool-pytest.json"; [ -z "$HOOK_OUT" ] && pass "C8d allow pytest = empty stdout" || fail "C8d pytest emitted: '$HOOK_OUT'"
hook pre-tool "$FX/cc-pre-tool-broken.json"; [ $HOOK_RC -eq 0 ] && [ -z "$HOOK_OUT" ] && pass "C8e fail-open on broken payload" || fail "C8e fail-open rc=$HOOK_RC out='$HOOK_OUT'"
hook post-tool "$FX/cc-post-tool-failure.json"; [ $HOOK_RC -eq 0 ] && pass "C8f PostToolUseFailure logged" || fail "C8f failure payload rc=$HOOK_RC"

echo "== Report =="
"${CTX[@]}" report --week --json | python3 -c '
import json,sys
d=json.load(sys.stdin)
need="sessions resident_tokens_avg questions questions_useful_ratio assumptions corrections cards_open cards_closed evidence_fill_ratio gate_blocks gate_overrides guard_deny guard_ask workers candidates_pending candidates_approved candidates_rejected stale_items searches search_cited_ratio".split()
missing=[k for k in need if k not in d]
print("missing:",missing) if missing else None
sys.exit(1 if missing else 0)
' && pass "C9 report keys" || fail "C9 report keys"

echo
[ $FAIL -eq 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $FAIL
