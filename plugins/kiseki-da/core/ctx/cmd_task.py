"""cmd_task.py — `task …`, `task override` and `verify run`: task cards, closing them, and command evidence.

Heavier modules (taskcard, evidence) are imported lazily inside the commands, as before the split.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from core.ctx.cli_common import _emit_json, _err, _json, _make_store, _out
from core.ctx.store import UserError, redact


# Fixed English reasons from taskcard.check_evidence / close → Japanese for the CLI
# (stdout `<Cn>: <reason>`, one Japanese line on stderr, exit 1)
REASON_JA = {
    "no evidence": "証拠がありません",
    "evidence not found": "証拠イベントが見つかりません",
    "not a tool call": "ツール呼出のイベントではありません",
    "tool mismatch": "ツールが一致しません",
    "command mismatch": "コマンドが一致しません",
    "command failed": "コマンドが失敗しています",
    "no criteria": "完了条件がありません",
    "result unknown": "成功状態が不明です",
    "unbound evidence": "対象・実行IDを確認できない旧形式の証拠です。検証を再実行してください",
    "request mismatch": "検査対象または引数が一致しません",
    "artifact changed": "証拠を取得した後に対象ファイルが変わっています",
    "workspace mismatch": "証拠の案件が一致しません",
    "evidence stale": "証拠の取得後に変更操作があります。再検証してください",
    "evidence predates task": "タスク作成前の証拠です",
}


def cmd_task_override(args) -> int:
    from core.ctx import evidence as authority, taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    if args.command_text is not None:
        tool, data = "Bash", {"command": args.command_text}
    else:
        tool = args.tool
        try:
            data = json.loads(args.tool_input)
        except (ValueError, TypeError):
            raise UserError("--input はツール引数の JSON オブジェクトで指定してください") from None
        if not tool or not isinstance(data, dict):
            raise UserError("--tool と --input を指定してください")
    ref = authority.record_override(st, card, tool, data, args.quote)
    _emit_json({"id": ref}) if _json(args) else _out(ref)
    return 0


def _card_summary(card) -> str:
    lines = [f"{card.id}\t{card.status}\t{card.risk}\t{card.updated}"]
    for c in card.criteria:
        lines.append(f"{c.id}\t{c.claim}\t{c.check}\t{c.evidence}\t{c.status}")
    return "\n".join(lines)


def _card_dict(card) -> dict:
    from dataclasses import asdict
    return asdict(card)


def _split_criterion(spec: str) -> tuple[str, str]:
    if " :: " not in spec:
        raise UserError('--add-criterion は "<claim> :: <check>" の形式で指定してください')
    claim, check = spec.split(" :: ", 1)
    claim, check = claim.strip(), check.strip()
    if not claim or not check:
        raise UserError('--add-criterion は "<claim> :: <check>" の形式で指定してください')
    return claim, check


def _split_evidence(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise UserError("--evidence は <Cn>=<ev:sid:seq>|last|last:<tool> の形式で指定してください")
    cid, ref = spec.split("=", 1)
    cid, ref = cid.strip(), ref.strip()
    if not cid or not ref:
        raise UserError("--evidence は <Cn>=<ev:sid:seq>|last|last:<tool> の形式で指定してください")
    return cid, ref


def cmd_task_new(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.new_card(st, args.goal, risk=args.risk, kind=args.kind, id=args.id)
    path = st.task_path(card.id)
    if _json(args):
        _emit_json({"id": card.id, "path": str(path)})
    else:
        _out(f"{card.id}\t{path}")
    return 0


def cmd_task_show(args) -> int:
    from core.ctx import taskcard
    card = taskcard.load(_make_store(args), args.id)
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(taskcard.render(card))
    return 0


def cmd_task_list(args) -> int:
    from core.ctx import taskcard
    status = None if args.status == "all" else args.status
    cards = taskcard.list_cards(_make_store(args), status)
    if _json(args):
        _emit_json([{"id": c.id, "status": c.status, "risk": c.risk, "kind": c.kind,
                     "updated": c.updated, "goal": c.goal, "workspace": c.workspace} for c in cards])
    else:
        _out("\n".join(f"{c.id}\t{c.status}\t{c.risk}\t{c.updated}" for c in cards))
    return 0


def cmd_task_set(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    did = False
    if args.status:
        taskcard.set_status(st, card, args.status)
        did = True
    if args.risk:
        taskcard.set_risk(st, card, args.risk)
        did = True
    if args.workspace:
        taskcard.set_workspace(st, card, args.workspace)
        did = True
    for constraint in args.constraint or []:
        taskcard.add_constraint(st, card, constraint)
        did = True
    if args.next_action:
        taskcard.set_next(st, card, args.next_action)
        did = True
    for spec in args.add_criterion or []:
        claim, check = _split_criterion(spec)
        taskcard.add_criterion(st, card, claim, check)
        did = True
    for spec in args.evidence or []:
        cid, ref = _split_evidence(spec)
        taskcard.set_evidence(st, card, cid, ref)
        did = True
    if args.assume:
        taskcard.add_assumption(st, card, args.assume)
        did = True
    if args.question:
        taskcard.add_question(st, card, args.question)
        did = True
    if args.decide:
        taskcard.add_decision(st, card, args.decide)
        did = True
    if args.note:
        taskcard.add_note(st, card, args.note)
        did = True
    if not did:
        raise UserError("更新内容を指定してください（--status / --risk / --add-criterion / --evidence / "
                        "--assume / --question / --decide / --note / --workspace）")
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(_card_summary(card))
    return 0


def cmd_task_close(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    missing = taskcard.close(st, card)
    if not missing:
        if _json(args):
            _emit_json({"id": card.id, "status": card.status})
        else:
            _out("OK")
        return 0
    items = []
    for m in missing:
        cid, _, reason = m.partition(": ")
        items.append({"criterion": cid, "reason": reason})
    if _json(args):
        _emit_json({"id": card.id, "status": card.status, "missing": items})
    else:
        _out("\n".join(f"{it['criterion']}: {REASON_JA.get(it['reason'], it['reason'])}" for it in items))
    _err("完了条件がありません" if any(it["reason"] == "no criteria" for it in items)
         else "完了条件の証拠が不足しています")
    return 1


def cmd_task_defer(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    taskcard.defer(st, card, args.reason)
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(_card_summary(card))
    return 0


def cmd_task_brief(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    text = taskcard.brief(st, card, args.role, args.scope)
    if _json(args):
        _emit_json({"id": card.id, "role": args.role, "text": text})
    else:
        _out(text)
    return 0


def cmd_verify_run(args) -> int:
    """Run argv without a shell and emit a trustworthy command evidence event."""
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise UserError("verify run -- の後に実行するコマンドを指定してください")
    store = _make_store(args)
    try:
        proc = subprocess.run(command, cwd=Path.cwd(), text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=args.timeout, check=False)
        stdout, stderr, returncode = proc.stdout or "", proc.stderr or "", int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout) or ""
        stderr = (exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else exc.stderr) or ""
        stderr += f"\n{args.timeout}秒でタイムアウトしました"
        returncode = 124
    except OSError as exc:
        stdout, stderr, returncode = "", str(exc), 127
    output = stdout + stderr
    display = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
    from core.ctx import evidence as E
    import uuid
    store.append_event({
        "tool_use_id": "verify-" + uuid.uuid4().hex,
        "workspace": store.workspace(), "cwd": str(Path.cwd()),
        "request_hash": E.identity("Bash", {"command": display}, str(Path.cwd())),
        "argv_request_hash": E.identity("Bash", {"command": shlex.join(command)}, str(Path.cwd())),
        "effect": E.effect("Bash", {"command": display}),
        "type": "tool_call",
        "tool": "Bash",
        "target": redact(display)[:200],
        "ok": returncode == 0,
        "out_len": len(output),
        "out_hash": hashlib.sha256(output.encode("utf-8", "replace")).hexdigest()[:12],
    })
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return returncode
