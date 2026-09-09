"""Tool request identity, conservative effects, and externally observable result checks.

No command is executed here. Hashes bind evidence to inputs without storing secrets.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import sys
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
        command = shell_command(data)
        # Keep operator-bearing scripts distinct from quoted literal arguments.
        data = {"command": (words(command) if simple_words(command) else command.strip()) or command.strip()}
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


def matches(event: dict, check: str, cwd: str) -> bool:
    wanted = expected(check, cwd)
    if wanted is None:
        return False
    if event.get("request_hash") == wanted:
        return True
    # The no-shell runner derives both renderings from the very same executed
    # argv. Keep only hashes, and preserve existing Windows criterion strings.
    return (str(event.get("tool_use_id", "")).startswith("verify-")
            and event.get("argv_request_hash") == wanted)


def simple_words(command: str) -> list[str]:
    """Parse a literal single invocation, never evaluate shell syntax or expansion.

    Backslashes in Windows paths remain intact. Ambiguous quoting, expansion,
    pipelines, redirection and scripts are deliberately unclassified.
    """
    command = command.strip()
    if command.startswith("& ") or command.startswith("&\t"):
        command = command[1:].lstrip()  # PowerShell call operator, only at the start
    args, token, quote, started = [], "", None, False
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == quote:
                if quote == "'" and command[i:i + 2] == "''":
                    token += "'"
                    i += 2
                    continue
                quote = None
            elif quote == '"' and (ch in "$`" or command[i:i + 2] == '\\"'):
                return []
            else:
                token += ch
        elif ch in "'\"":
            quote, started = ch, True
        elif ch in ";&|<>`\n\r$(){}#":
            return []
        elif ch.isspace():
            if started:
                args.append(token)
                token, started = "", False
        else:
            token += ch
            started = True
        i += 1
    if quote:
        return []
    if started:
        args.append(token)
    return args


def shell_command(tool_input: dict) -> str:
    return str(tool_input.get("command", tool_input.get("cmd", "")))


def _executable(raw: str, cwd: str) -> Path | None:
    if "/" in raw or "\\" in raw:
        return Path(absolute(raw, cwd or "."))
    found = shutil.which(raw)
    return Path(found).resolve() if found else None


def python_script(args: list[str], cwd: str = "", *, trusted: bool = True) -> int | None:
    if not args:
        return None
    if trusted:
        if _executable(args[0], cwd) != Path(sys.executable).resolve():
            return None
    elif not re.fullmatch(r"(?:python(?:\d+(?:\.\d+)*)?|py)(?:\.exe)?", Path(args[0]).name, re.I):
        return None
    i = 1
    while i < len(args) and args[i] in {"-B", "-I", "-u", "-E", "-s"}:
        i += 1
    return i if i < len(args) and not args[i].startswith("-") else None


def _managed_launcher(path: Path | None) -> bool:
    """Installer-owned launchers and bootstrap must still match their saved hashes."""
    if path is None:
        return False
    from core.ctx.store import kiseki_da_home
    home = kiseki_da_home()
    try:
        metadata = json.loads((home / "install.json").read_text(encoding="utf-8"))
        current = json.loads((home / "current.json").read_text(encoding="utf-8"))
        runtime = Path(current["runtime"]).resolve()
        if not runtime.is_relative_to(home / "runtime"):
            return False
        selected = runtime / "plugins/kiseki-da/core/ctx"
        for filename in ("evidence.py", "cli.py"):
            if (selected / filename).read_bytes() != Path(__file__).with_name(filename).read_bytes():
                return False
        records = {Path(row["path"]).resolve(): row["sha256"]
                   for row in metadata.get("management_launchers", [])}
        bootstrap = home / "bin/kiseki-da.py"
        return all(p in records and hashlib.sha256(p.read_bytes()).hexdigest() == records[p]
                   for p in (path, bootstrap))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ctx_args(command: str, cwd: str = "", *, trusted: bool = True) -> list[str]:
    args = simple_words(command)
    i = python_script(args, cwd, trusted=trusted)
    if i is not None:
        script = Path(absolute(args[i], cwd or "."))
        if script == Path(__file__).resolve().with_name("cli.py") or (trusted and _managed_launcher(script)):
            return args[i + 1:]
    if trusted and args and _managed_launcher(_executable(args[0], cwd)):
        return args[1:]
    return []


def is_ctx(command: str, cwd: str = "") -> bool:
    return bool(ctx_args(command, cwd))


def ctx_command(command: str, cwd: str = "", *, trusted: bool = True) -> str | None:
    args = ctx_args(command, cwd, trusted=trusted)
    i = 0
    while i < len(args):
        if args[i] in ("--home", "--sid"):
            i += 2
        elif args[i] == "--json":
            i += 1
        elif args[i].startswith(("--sid=", "--home=")):
            i += 1
        else:
            return args[i]
    return None


def metadata_command(command: str, cwd: str = "") -> bool:
    args = ctx_args(command, cwd)
    while args:
        if args[0] in {"--home", "--sid"}:
            args = args[2:]
        elif args[0] == "--json" or args[0].startswith(("--home=", "--sid=")):
            args = args[1:]
        else:
            break
    if not args:
        return False
    if args[0] in {"search", "report", "build", "version"}:
        return True
    if args[0] == "doctor":
        return all(arg == "--json" for arg in args[1:])
    allowed = {"context": {"required", "instruction", "profile"},
               "task": {"new", "set", "show", "list", "close", "defer", "brief", "override"},
               "policy": {"show"}, "persona": {"show", "pack"},
               "candidate": {"list", "show"}, "session": {"list"}, "skills": {"list", "show"}}
    return len(args) > 1 and args[1] in allowed.get(args[0], set())


def effect(tool: str, tool_input: dict, cwd: str = "") -> str:
    name = tool.lower()
    if name in READ_TOOLS:
        return "read"
    if name in WRITE_TOOLS or "file_paths" in tool_input:
        return "write"
    if name not in SHELL_TOOLS:
        return "unknown"
    command = shell_command(tool_input)
    if metadata_command(command, cwd):
        return "metadata"
    args = simple_words(command)
    if not args:
        return "unknown"
    head = Path(args[0]).name.lower()
    if head in {"remove-item", "set-content", "add-content", "out-file", "copy-item", "move-item", "new-item"}:
        return "write"
    if head in {"get-content", "get-childitem", "get-item", "get-location", "get-filehash",
                "test-path", "select-string", "sls", "gc", "gci", "pwd", "dir"}:
        return "read"
    if head in {"rm", "mv", "cp", "mkdir", "rmdir", "touch", "tee", "chmod", "chown"}:
        return "write"
    if head == "rg" and any(arg == "--pre" or arg.startswith("--pre=") for arg in args[1:]):
        return "unknown"
    if head in {"pytest", "cat", "head", "tail", "rg", "grep", "ls", "pwd", "wc", "stat", "diff"}:
        return "read"
    if head == "git" and len(args) > 1 and args[1] in {"diff", "status", "log", "show", "rev-parse"}:
        if any(arg == "--output" or arg.startswith("--output=") for arg in args[2:]):
            return "write"
        if "--ext-diff" in args or "--textconv" in args:
            return "unknown"
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
