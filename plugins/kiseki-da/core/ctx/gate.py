"""gate.py — pre-tool guard (deny/ask lists) and stop gate (INTERFACES.md §3, §6.2).

guard() evaluates pa_home() and REPO_ROOT / "core" at call time; stop_gate() writes exactly one `gate`
event per call (DECISIONS A-5, A-7, A-8, A-12). Depends on store and taskcard only; no I/O at import.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from core.ctx import store as _store
from core.ctx import taskcard
from core.ctx import evidence as E
from core.ctx.store import Store, UserError

# Commands that read a file's content; naming ~/.ssh, ~/.aws or a .env file as their argument is denied
# (A-5 / A-8: reads are denied, R3 words are asked). Writes such as `echo ... >> .env` are not matched.
_READERS = (
    r"cat|less|more|head|tail|bat|batcat|vi|vim|nvim|nano|emacs|code|open|strings|xxd|hexdump|od|"
    r"base64|grep|egrep|fgrep|rg|ag|awk|sed|cp|scp|rsync|source|type|gc|Get-Content"
)

# A Windows-style path prefix before a `\`-separated component: C: , ~ , . , .. , $VAR , ${VAR} , $env:VAR , %VAR%.
# Only such anchored paths count, so bash regex escapes like `grep '\.env'` or `cat foo\.env` are not reads of .env.
_WIN_ANCHOR = r"(?:[A-Za-z]:|~|\.\.?|\$env:\w+|\$\w+|\$\{[^}\s]*\}|%\w+%)"

DENY_PATTERNS: list[tuple[str, str]] = [   # (regex on command, reason)
    # rm with a recursive flag (any order: -rf, -fr, -r -f, --recursive, also after operands) and a target / , /* ,
    # ~ , $HOME or .. anywhere among the operands of the same command segment (`rm -rf dist build /` is denied too)
    (r"\brm\s+(?=(?:[^\s;&|]+[ \t]+)*(?:-[A-Za-z]*[rR]|--recursive))(?:[^\s;&|]+[ \t]+)+"
     r"[\"']?(?:/+|/\*|~/?|\$HOME/?|\$\{HOME\}/?|\.\./?)[\"']?/?(?=\s|$|[;&|)])",
     "ルート・ホーム・親ディレクトリの再帰削除（rm -rf）は禁止です"),
    # git push --force / -f to main or master, both within the same command segment (not across ; & | newline);
    # --force-with-lease is not --force and feature branches pass
    (r"\bgit\s+push\b(?=[^;&|\n]*\s(?:--force(?!-)|-f)\b)(?=[^;&|\n]*(?<![\w.-])(?:main|master)(?![\w/.-]))",
     "main/master への force push は禁止です（--force-with-lease は可）"),
    # curl / wget piped (directly or through other filters) into a shell, optionally via sudo
    (r"(?s)\b(?:curl|wget)\b.*\|\s*(?:sudo\s+(?:-\S+\s+)*)?(?:sh|bash|zsh|dash|ksh)\b",
     "ダウンロードした内容をそのままシェルで実行することは禁止です"),
    # Native Windows equivalents. Broad recursive/forced deletion is intentionally denied rather than guessed safe.
    (r"(?i)\b(?:Remove-Item|ri|rm|del|erase|rd|rmdir)\b"
     r"(?=[^;&|\n]*-(?:r|re|rec|recu|recur|recurs|recurse)\b)"
     r"(?=[^;&|\n]*-(?:f|fo|for|forc|force)\b)",
     "PowerShell の再帰・強制削除は禁止です"),
    (r"(?i)\b(?:rd|rmdir|del|erase)\b(?=[^;&|\n]*/s\b)(?=[^;&|\n]*/q\b)",
     "cmd.exe の再帰・強制削除は禁止です"),
    (r"(?is)\b(?:Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b.*\|\s*(?:Invoke-Expression|iex)\b",
     "ダウンロードした内容をそのまま PowerShell で実行することは禁止です"),
    (r"\bchmod\s+(?:-\S+\s+)*[0-7]?777\b", "chmod 777 は禁止です"),
    # reader command + a path component .ssh / .aws / .env in the same pipeline segment (.env.example etc. pass);
    # the component may follow `/` or, on an anchored Windows path (PowerShell), `\`
    (r"(?i)\b(?:" + _READERS + r")\b[^|;&\n]*(?:^|[\s\"'=:(])"
     r"(?:[^\s\"'|;&]*/|" + _WIN_ANCHOR + r"\\(?:[^\s\"'|;&\\]*\\)*)?"
     r"\.(?:ssh|aws|env(?!\.(?:example|sample|template|dist)\b))\b",
     "秘密情報（~/.ssh, ~/.aws, .env）の読取は禁止です"),
]
ASK_PATTERNS: list[tuple[str, str]] = [    # R3: whole words, case-insensitive
    (r"(?i)\b(?:deploy|publish|release)\b", "R3 操作（デプロイ・公開・リリース）の可能性があります。利用者の確認が必要です"),
    (r"(?i)\b(?:payment|pay)\b", "R3 操作（支払い）の可能性があります。利用者の確認が必要です"),
    (r"(?i)\b(?:delete|drop)\b", "R3 操作（削除）の可能性があります。利用者の確認が必要です"),
    (r"(?i)\b(?:prod|production)\b", "R3 操作（本番環境）の可能性があります。利用者の確認が必要です"),
    (r"(?i)\bsecrets?\b", "R3 操作（秘密情報）の可能性があります。利用者の確認が必要です"),
]
PATH_KEYS = ("file_path", "notebook_path", "path", "file_paths")

_SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
_WRITE_TOOLS = frozenset({"Write", "Edit", "NotebookEdit", "Delete"})
_BLOCKING_RISKS = frozenset({"R1", "R2", "R3"})
_DENY_RE = [(re.compile(p), reason) for p, reason in DENY_PATTERNS]
_ASK_RE = [(re.compile(p), reason) for p, reason in ASK_PATTERNS]


# ---------------------------------------------------------------- pre-tool guard

def _collect_paths(tool_input: dict) -> list[str]:
    out: list[str] = []
    for key in PATH_KEYS:
        v = tool_input.get(key)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            out.extend(x for x in v if isinstance(x, str))
    return [p for p in (s.strip() for s in out) if p]


def _resolve(raw: str, cwd: str) -> Path | None:
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute() and cwd:
            path = Path(cwd).expanduser() / path
        return path.resolve()
    except (OSError, ValueError, RuntimeError):
        return None


def guard(tool: str, tool_input: dict, cwd: str) -> tuple[Literal["allow", "ask", "deny"], str]:
    """§6.2 rules (1)-(3). pa_home() and REPO_ROOT / "core" are evaluated on every call."""
    tool = tool or ""
    if not isinstance(tool_input, dict):
        tool_input = {}
    if tool in _SHELL_TOOLS:
        raw = tool_input.get("command", "")
        command = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
        if E.ctx_command(command) == "hook":
            return "deny", "hook はホスト専用の入口です。利用者発言やツール証拠をモデルから作成しないでください"
        for rx, reason in _DENY_RE:
            if rx.search(command):
                return "deny", reason
        args = E.words(command)
        if args and args[0] in {"rg", "grep", "egrep", "fgrep"} and E.effect(tool, tool_input) == "read":
            return "allow", ""  # a search for 'deploy' is not a deployment
        if E.is_ctx(command):
            return "allow", ""  # quoted task text does not itself perform the quoted operation
        for rx, reason in _ASK_RE:
            if rx.search(command):
                return "ask", reason
        return "allow", ""
    if tool in _WRITE_TOOLS or "file_paths" in tool_input:
        home = _store.kiseki_da_home() if hasattr(_store, "kiseki_da_home") else _store.pa_home()
        core = (_store.REPO_ROOT / "core").resolve()
        for raw in _collect_paths(tool_input):
            path = _resolve(raw, cwd or "")
            if path is None:
                continue
            if path.is_relative_to(home):
                return "deny", f"$KISEKI_DA_HOME（{home}）配下への書込は禁止です: {raw}"
            if path.is_relative_to(core):
                return "deny", f"Kiseki DA の core/（{core}）配下への書込は禁止です: {raw}"
        if tool == "Delete":
            return "ask", "削除の対象を確認し、現在の利用者指示があれば今回の操作として記録してください"
        return "allow", ""
    if tool.lower().startswith("mcp"):
        action_name = re.sub(r"[_:]+", " ", tool.lower())
        if re.search(r"\b(send|publish|deploy|delete|drop|payment|pay)\b", action_name):
            return "ask", "外部への操作です。現在の明示指示を対象操作に結び付けてください"
    return "allow", ""


# ---------------------------------------------------------------- stop gate

def stop_gate(store: Store, sid: str, stop_hook_active: bool = False) -> tuple[bool, str]:
    """Exactly one `gate` event per call: task + blocked=true when blocking, task=null otherwise."""
    if stop_hook_active:
        store.append_event({"type": "gate", "task": None, "blocked": False, "reason": "stop_hook_active"})
        return False, ""
    referenced: dict[str, None] = {}   # cards touched in this session, in first-seen order
    already: set[str] = set()          # cards already blocked once in this session
    for ev in store.iter_events(types={"task_open", "task_update", "gate"}, sid=sid):
        task = ev.get("task")
        if not isinstance(task, str) or not task:
            continue
        if ev.get("type") == "gate":
            if ev.get("blocked"):
                already.add(task)
        else:
            referenced[task] = None
    open_cards: list[taskcard.TaskCard] = []
    for task in referenced:
        if task in already:
            continue
        try:
            card = taskcard.load(store, task)
        except (UserError, OSError, ValueError):
            continue   # card file removed or unreadable
        if card.status == "open" and card.risk in _BLOCKING_RISKS:
            open_cards.append(card)
    if open_cards:
        card = max(open_cards, key=lambda c: (c.updated, c.id))   # A-7: newest `updated` first
        reason = (f"open な {card.risk} カード {card.id} があります。閉じるか保留してください: "
                  f"kiseki-da task close {card.id} --sid {sid} / "
                  f"kiseki-da task defer {card.id} --reason <未検証の理由> --sid {sid}")
        store.append_event({"type": "gate", "task": card.id, "blocked": True, "reason": reason})
        return True, reason
    store.append_event({"type": "gate", "task": None, "blocked": False, "reason": ""})
    return False, ""
