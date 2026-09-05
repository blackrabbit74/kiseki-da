"""Tool request identity, conservative effects, and externally observable result checks.

No command is executed here. Hashes bind evidence to inputs without storing secrets.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path

READ_TOOLS = frozenset({"read", "grep", "glob", "webfetch", "websearch", "view_image"})
SHELL_TOOLS = frozenset({"bash", "powershell", "shell", "exec_command"})
WRITE_TOOLS = frozenset({"write", "edit", "notebookedit", "delete", "apply_patch"})


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                                     separators=(",", ":")).encode()).hexdigest()


def words(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def absolute(path: str, cwd: str) -> str:
    p = Path(path).expanduser()
    return str((p if p.is_absolute() else Path(cwd) / p).resolve())


def identity(tool: str, tool_input: dict, cwd: str) -> str:
    name = tool.lower()
    data = dict(tool_input)
    if name in SHELL_TOOLS:
        name = "bash"
        data = {"command": words(str(data.get("command", ""))) or str(data.get("command", "")).strip()}
    elif name == "read":
        raw = str(data.get("file_path") or data.get("path") or "")
        data = {"file_path": absolute(raw, cwd)}
        # Partial reads do not establish that an entire file was checked.
        for k in ("offset", "limit"):
            if k in tool_input:
                data[k] = tool_input[k]
    return digest({"tool": name, "input": data, "cwd": absolute(cwd or ".", ".")})


def expected(check: str, cwd: str) -> str | None:
    head, _, rest = check.strip().partition(" ")
    name = head.lower()
    if not head:
        return None
    if rest.lstrip().startswith("{"):
        try:
            data = json.loads(rest)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        actual_cwd = str(data.pop("cwd", cwd))
        return identity(head, data, absolute(actual_cwd, cwd))
    if name == "read":
        args = words(rest)
        if len(args) != 1:
            return None
        return identity("Read", {"file_path": args[0]}, cwd)
    if name in READ_TOOLS or name.startswith("mcp"):
        return None  # non-shell tools require their exact JSON arguments
    return identity("Bash", {"command": check}, cwd)


def is_ctx(command: str) -> bool:
    args = words(command)
    return len(args) >= 3 and Path(args[1]).resolve() == Path(__file__).resolve().with_name("cli.py")


def ctx_command(command: str) -> str | None:
    if not is_ctx(command):
        return None
    args = words(command)
    i = 2
    while i < len(args):
        if args[i] in ("--home", "--sid"):
            i += 2
        elif args[i] == "--json":
            i += 1
        else:
            return args[i]
    return None


def effect(tool: str, tool_input: dict) -> str:
    name = tool.lower()
    if name in READ_TOOLS:
        return "read"
    if name in WRITE_TOOLS or "file_paths" in tool_input:
        return "write"
    if name not in SHELL_TOOLS:
        return "unknown"
    command = str(tool_input.get("command", ""))
    if is_ctx(command):
        return "metadata"
    args = words(command)
    if not args or re.search(r"[;&|<>`\n]|\$\(", command):
        return "unknown"
    head = Path(args[0]).name.lower()
    if head in {"rm", "mv", "cp", "mkdir", "rmdir", "touch", "tee", "chmod", "chown"}:
        return "write"
    if head in {"pytest", "cat", "head", "tail", "rg", "grep", "ls", "pwd", "wc", "stat", "diff"}:
        return "read"
    if head == "git" and len(args) > 1 and args[1] in {"diff", "status", "log", "show", "rev-parse"}:
        return "read"
    if head in {"python", "python3"} and args[1:3] in (["-m", "pytest"], ["-m", "unittest"]):
        return "read"
    if head in {"npm", "pnpm", "yarn"} and args[1:2] in (["test"], ["lint"]):
        return "read"
    return "unknown"


def file_snapshot(tool: str, tool_input: dict, cwd: str) -> dict | None:
    if tool.lower() != "read":
        return None
    path = Path(absolute(str(tool_input.get("file_path") or tool_input.get("path") or ""), cwd))
    try:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return None
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except OSError:
        return None


def changed(snapshot: dict) -> bool:
    try:
        return hashlib.sha256(Path(snapshot["path"]).read_bytes()).hexdigest() != snapshot["sha256"]
    except (OSError, KeyError):
        return True


from core.ctx.store import UserError


def cancels(prompt: str) -> bool:
    return bool(re.search(r"^(中止|やめて|待って|キャンセル|stop\b|cancel\b)", prompt.strip(), re.I)
                or re.search(r"(しないで|待って|中止して)[。！!\s]*$", prompt))


def user_quote(store, quote: str | None) -> dict:
    current = store.user_input()
    if not quote or not current or quote.strip() != current.get("prompt", "").strip():
        raise UserError("対応する利用者指示を確認できません。kiseki-da context instruction で受信済みの操作指示を確認してください（user-input hook が必要です）")
    if current.get("workspace") != store.workspace():
        raise UserError("現在の案件で受け取った利用者発言を使ってください")
    return current


def global_memory(store, quote: str | None, text: str) -> dict:
    current = user_quote(store, quote)
    prompt = current["prompt"]
    if not (re.match(r"^(?:今後(?:は)?[、, ]*)?(?:全案件(?:で|に)|共通(?:の)?(?:ルール|記憶)?(?:で|として|に)|グローバル(?:に|で)|remember globally)", prompt.strip(), re.I)
            and (re.search(r"(?:覚えて|記憶して|保存して|ルールにして)(?:おいて)?(?:ください|くれる|もらえる|もらえますか)?[。！!？?\s]*$", prompt)
                 or prompt.lower().startswith("remember globally "))):
        raise UserError("共通の記憶への昇格には、全案件で覚えるという利用者の明示指示が必要です")
    if text not in prompt:
        raise UserError("共通で覚える本文が利用者の発言に含まれていません。案件限定の内容を推測で広げません")
    return current


def record_override(store, card, tool: str, tool_input: dict, quote: str) -> str:
    current = user_quote(store, quote)
    if cancels(quote):
        raise UserError("中止・保留の発言を実行許可として使うことはできません")
    if not card.workspace or card.workspace != store.workspace():
        raise UserError("今の案件に属するカードに実行指示を記録してください")
    return store.append_event({"type": "human_override", "task": card.id, "workspace": card.workspace,
                               "request_hash": identity(tool, tool_input, card.workspace),
                               "user_input_id": current["id"], "quote": quote,
                               "reason": "現在の明示指示を過去のDA判断より優先する"})


def consume_override(store, tool: str, tool_input: dict, cwd: str) -> str | None:
    current = store.user_input()
    if not current:
        return None
    request_hash = identity(tool, tool_input, cwd)
    events = list(store.iter_events(sid=store.effective_sid()))
    consumed = {ev.get("authority_ref") for ev in events if ev.get("type") == "authority_used"}
    for ev in reversed(events):
        ref = f"ev:{ev.get('sid')}:{ev.get('seq')}"
        if (ev.get("type") == "human_override" and ref not in consumed
                and ev.get("user_input_id") == current["id"] and ev.get("request_hash") == request_hash
                and ev.get("workspace") == store.workspace()):
            store.append_event({"type": "authority_used", "authority_ref": ref, "request_hash": request_hash})
            return ref
    return None
