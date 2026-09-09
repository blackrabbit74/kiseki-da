"""store.py — constants, Kiseki DA state I/O, TOML emitter and validation.

Every write under ``KISEKI_DA_HOME`` goes through this module.
Other modules must not redefine the constants declared here.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import functools
import json
import os
import re
import shutil
import secrets
import tomllib
from pathlib import Path
from typing import Iterator, Literal

try:
    import fcntl as _fcntl
except ImportError:  # Windows
    _fcntl = None
try:
    import msvcrt as _msvcrt
except ImportError:  # POSIX
    _msvcrt = None

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

EVENT_TYPES: frozenset[str] = frozenset({
    "session_start", "session_end", "context_manifest",
    "task_open", "task_update", "task_close",
    "question", "assumption", "tool_call", "evidence",
    "gate", "guard", "correction", "capture", "candidate", "approval",
    "worker_dispatch", "worker_return", "search", "proposal", "error",
    "user_input", "human_override", "authority_used", "context_read",
})
LOG_TYPES = ("correction", "worker_return", "proposal", "error")
CANDIDATE_KINDS = ("constraint", "preference", "goal", "fact")
CANDIDATE_STATUSES = ("pending", "approved", "rejected")
KIND_TO_SECTION = {"constraint": "constraints", "preference": "preferences", "goal": "goals", "fact": "facts"}
SECTIONS = ("constraints", "preferences", "goals", "facts")
DEFAULT_REVIEW_DAYS = {"constraints": 180, "preferences": 180, "goals": 90, "facts": 365}
# Source priority, highest first (ARCHITECTURE §5.4). `document:<ref>` sources rank as "document".
SOURCE_ORDER = ("user-stated", "approved-inference", "document")
SNAPSHOT_KEEP = 30
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
EVENT_ID_RE = re.compile(r"^ev:(?P<sid>.+):(?P<seq>\d+)$")


class UserError(Exception):
    """User or spec violation. The CLI prints str(exc) (one Japanese line) to stderr and exits 1."""


# ---------------------------------------------------------------- helpers

def kiseki_da_home() -> Path:
    """Evaluate KISEKI_DA_HOME (or ~/.kiseki-da) on every call."""
    raw = os.environ.get("KISEKI_DA_HOME")
    return (Path(raw).expanduser() if raw else Path.home() / ".kiseki-da").resolve()


def pa_home() -> Path:
    """Backward-compatible function name; legacy PA_HOME is intentionally ignored."""
    return kiseki_da_home()


def legacy_home_signal() -> Path | None:
    """Return a legacy state location for an explicit migration prompt only.

    The returned path is never selected as the active store and this function
    performs no writes or imports.
    """
    raw = os.environ.get("PA_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    legacy = (Path.home() / ".pa").resolve()
    return legacy if legacy.exists() else None


def estimate_tokens(text: str) -> int:
    """The only token estimate in the repository: round(ascii/4 + non_ascii/1.6)."""
    ascii_n = sum(1 for ch in text if ord(ch) < 128)
    return round(ascii_n / 4 + (len(text) - ascii_n) / 1.6)


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> _dt.date:
    return _dt.date.today()


_REDACT_RES = (
    re.compile(r"(api[_-]?key|token|secret|password)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"--(?:api[_-]?key|token|password)\s+\S+", re.IGNORECASE),
    re.compile(r"https?://[^\s/:@]+:[^\s/@]+@[^\s]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"),
)


def redact(s: str) -> str:
    for pattern in _REDACT_RES:
        s = pattern.sub("[REDACTED]", s)
    return s


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def parse_ts(value) -> _dt.datetime | None:
    """ISO 8601 → aware datetime (naive values are taken as local time). None if unparsable."""
    if not isinstance(value, str):
        return None
    try:
        d = _dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    return d if d.tzinfo is not None else d.astimezone()


def parse_date(value) -> _dt.date:
    """'YYYY-MM-DD' (or a date object) → date; UserError otherwise."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError:
        raise UserError(f"日付は YYYY-MM-DD 形式で指定してください: {value}") from None


def parse_event_id(ev_id: str) -> tuple[str, int] | None:
    m = EVENT_ID_RE.match(ev_id or "")
    return (m.group("sid"), int(m.group("seq"))) if m else None


def source_rank(source: str | None) -> int:
    """0 = user-stated, 1 = approved-inference, 2 = document:* / anything else."""
    if source == "user-stated":
        return 0
    if source == "approved-inference":
        return 1
    return 2


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(dumps(rec) + "\n")


def _lock(fd: int) -> bool:
    """Take an exclusive advisory lock on `fd` (blocking). False when the platform has none."""
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_EX)
            return True
        if _msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
            return True
    except OSError:
        pass
    return False


def _unlock(fd: int) -> None:
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        elif _msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
    except OSError:
        pass


@contextlib.contextmanager
def _locked_append(path: Path) -> Iterator:
    """Open `path` for appending and hold an exclusive lock on it for the block.

    Concurrent hook processes of one session (parallel tool calls) share `session/<sid>.seq`;
    the lock on the append-only file (its inode is never replaced) serialises
    read-increment-write of the counter and the JSONL append. Best effort: without a usable
    lock the block still runs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        locked = _lock(f.fileno())
        try:
            yield f
            f.flush()
        finally:
            if locked:
                _unlock(f.fileno())


def _iter_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s) or "_"


def _num_suffix(s: str) -> int:
    m = re.search(r"(\d+)$", s or "")
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------- TOML emitter

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(k: str) -> str:
    return k if _BARE_KEY.match(k) else _toml_str(k)


def _toml_str(s: str) -> str:
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ord(ch) < 0x20 or ch == "\x7f":
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("non-finite float is not representable")
        return repr(v)
    if isinstance(v, _dt.datetime):
        if v.tzinfo is None:  # TOML local date-time from a hand edit: local time, as parse_ts reads it
            v = v.astimezone()
        return v.isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, _dt.time):
        return v.isoformat()
    if isinstance(v, str):
        return _toml_str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        values = [f"{_toml_key(str(k))} = {_toml_value(value)}"
                  for k, value in v.items() if value is not None]
        return "{ " + ", ".join(values) + " }"
    raise TypeError(f"unsupported TOML value: {type(v).__name__}")


def emit_toml(data: dict) -> str:
    """Minimal emitter: (a) top-level scalars, (b) one-level tables, (c) array tables.

    Empty top-level lists are omitted (read_profile fills them back with []).
    None values inside items are skipped.
    """
    scalars: list[tuple[str, object]] = []
    tables: list[tuple[str, dict]] = []
    arrays: list[tuple[str, list]] = []
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, dict):
            tables.append((k, v))
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            arrays.append((k, v))
        elif isinstance(v, list) and not v:
            if k not in SECTIONS:
                scalars.append((k, v))
        else:
            scalars.append((k, v))
    out: list[str] = []
    for k, v in scalars:
        out.append(f"{_toml_key(k)} = {_toml_value(v)}")
    for k, tbl in tables:
        if out:
            out.append("")
        out.append(f"[{_toml_key(k)}]")
        for kk, vv in tbl.items():
            if vv is None:
                continue
            out.append(f"{_toml_key(kk)} = {_toml_value(vv)}")
    for k, items in arrays:
        for item in items:
            out.append("")
            out.append(f"[[{_toml_key(k)}]]")
            for kk, vv in item.items():
                if vv is None:
                    continue
                out.append(f"{_toml_key(kk)} = {_toml_value(vv)}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- validation table
# Compile required keys and types from core/schema/*.json; one cached load per process.

_SCHEMA_FILES = {"profile": "profile", "event": "event", "candidate": "candidate", "task": "task-card"}


def _schema_type(spec: dict):
    types = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
             "object": dict, "array": list, "null": type(None)}
    names = spec.get("type", [])
    names = [names] if isinstance(names, str) else names
    out = []
    for name in names:
        typ = types[name]
        out.extend(typ if isinstance(typ, tuple) else (typ,))
    if spec.get("format") in ("date", "date-time") and str in out:
        out.append(_dt.date)
    return out[0] if len(out) == 1 else tuple(out)


def _schema_table(spec: dict) -> dict:
    required = set(spec.get("required", []))
    return {kind: {key: _schema_type(value) for key, value in spec.get("properties", {}).items()
                   if "type" in value and (key in required) == (kind == "required")}
            for kind in ("required", "optional")}


@functools.lru_cache(maxsize=16)
def _schema_tables(kind: str, root: str) -> tuple[dict, dict]:
    # JSON files own required keys and types. Compile once per process, keeping hook I/O bounded.
    path = Path(root) / "core/schema" / (_SCHEMA_FILES[kind] + ".schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    item = schema.get("$defs", {}).get("item" if kind == "profile" else "criterion", {})
    return _schema_table(schema), _schema_table(item)


def _check_obj(schema: dict, obj: dict, prefix: str, errors: list[str]) -> None:
    for key, typ in schema["required"].items():
        if key not in obj:
            errors.append(f"{prefix}{key}: 必須キーがありません")
        elif not _is_type(obj[key], typ):
            errors.append(f"{prefix}{key}: 型が不正です（{type(obj[key]).__name__}）")
    for key, typ in schema["optional"].items():
        if key in obj and not _is_type(obj[key], typ):
            errors.append(f"{prefix}{key}: 型が不正です（{type(obj[key]).__name__}）")


def _is_type(value, typ) -> bool:
    if typ is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(typ, tuple) and int in typ and float in typ:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, typ)


# ---------------------------------------------------------------- Store

class Store:
    def __init__(self, home: Path | None = None, sid: str | None = None,
                 common_home: Path | None = None, project_id: str | None = None):
        self.home = Path(home).expanduser().resolve() if home is not None else kiseki_da_home()
        self.sid = sid
        self.common_home = (Path(common_home).expanduser().resolve() if common_home is not None else self.home)
        self.project_id = project_id

    @property
    def is_project(self) -> bool:
        return self.project_id is not None and self.common_home != self.home

    def global_store(self) -> "Store":
        """Return the common user store (self in user scope)."""
        if not self.is_project:
            return self
        return Store(home=self.common_home, sid=self.sid)

    @classmethod
    def for_cwd(cls, cwd: str | os.PathLike[str] | None, *, home: Path | None = None,
                sid: str | None = None) -> "Store | None":
        """Resolve an activation-aware store without writing any state."""
        from core.ctx.scope import scoped_store
        return scoped_store(home, cwd, sid=sid)

    # paths
    @property
    def profile_path(self) -> Path:
        return self.home / "profile.toml"

    @property
    def events_path(self) -> Path:
        return self.home / "events.jsonl"

    @property
    def candidates_path(self) -> Path:
        return self.home / "candidates.jsonl"

    @property
    def archive_path(self) -> Path:
        return self.home / "archive" / "profile-superseded.jsonl"

    # ------------------------------------------------------------ init / profile
    def _ensure_home(self) -> None:
        """Create the home as a private area (mode 700) when a write happens before `kiseki-da init`.

        An existing directory is left as it is; `init` is the place that fixes modes up.
        """
        if self.home.is_dir():
            return
        self.home.mkdir(parents=True, exist_ok=True)
        os.chmod(self.home, 0o700)

    def init(self, force: bool = False) -> list[Path]:
        created: list[Path] = []
        if not self.home.exists():
            self.home.mkdir(parents=True, exist_ok=True)
            created.append(self.home)
        os.chmod(self.home, 0o700)
        for sub in ("tasks", "archive", "snapshots", "session"):
            p = self.home / sub
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                created.append(p)
        example = REPO_ROOT / "state.example" / "profile.toml"
        if self.profile_path.exists():
            if not force:
                raise UserError(f"profile.toml は既にあります（上書きするには --force）: {self.profile_path}")
            self.snapshot()
        _atomic_write(self.profile_path, example.read_text(encoding="utf-8"))
        created.append(self.profile_path)
        return created

    def read_profile(self) -> dict:
        """Parse this store's profile; missing item sections are filled with []."""
        if not self.profile_path.exists():
            data: dict = {"schema": 1, "identity": {}, "da": {}}
        else:
            try:
                with open(self.profile_path, "rb") as f:
                    data = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise UserError(f"profile.toml を読めません: {e}") from None
        data.setdefault("schema", 1)
        data.setdefault("identity", {})
        data.setdefault("da", {})
        for s in SECTIONS:
            v = data.get(s)
            data[s] = list(v) if isinstance(v, list) else []
        return data

    def read_effective_profile(self) -> dict:
        """Return the inherited profile visible to this store.

        Project scope inherits only common identity, constraints, and
        preferences.  Persona, project preferences/facts/goals, candidates,
        tasks, and events remain isolated in the project store.
        """
        local = self.read_profile()
        if not self.is_project:
            return local
        common = self.global_store().read_profile()
        effective = dict(local)
        effective["schema"] = max(int(common.get("schema", 1)), int(local.get("schema", 1)))
        effective["identity"] = dict(common.get("identity") or {})
        effective["da"] = dict(local.get("da") or {})
        effective["persona"] = dict(local.get("persona") or {})
        effective["constraints"] = [*(common.get("constraints") or []), *(local.get("constraints") or [])]
        effective["preferences"] = [*(common.get("preferences") or []), *(local.get("preferences") or [])]
        effective["goals"] = [*(common.get("goals") or []), *(local.get("goals") or [])]
        effective["facts"] = [*(common.get("facts") or []), *(local.get("facts") or [])]
        return effective

    def write_profile(self, data: dict) -> None:
        errors = self.validate("profile", data)
        if errors:
            raise UserError("profile.toml の形式が不正です: " + "; ".join(errors))
        self._ensure_home()
        if self.profile_path.exists():
            self.snapshot()
        _atomic_write(self.profile_path, emit_toml(data))

    def snapshot(self) -> Path:
        if not self.profile_path.exists():
            raise UserError("profile.toml がありません（先に kiseki-da init を実行してください）")
        d = self.home / "snapshots"
        d.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
        dst = d / f"profile-{stamp}.toml"
        n = 0
        while dst.exists():
            n += 1
            # A suffix after '~' sorts after the unsuffixed '.toml' on every OS.
            dst = d / f"profile-{stamp}~{n:06d}.toml"
        shutil.copy2(self.profile_path, dst)
        for old in sorted(d.glob("profile-*.toml"))[:-SNAPSHOT_KEEP]:
            old.unlink(missing_ok=True)
        return dst

    def new_profile_id(self, section: str) -> str:
        """Prefix c/p/g/f + (max number of that kind in profile and archive) + 1. Ids are never reused."""
        if section not in SECTIONS:
            raise UserError(f"セクションが不正です: {section}")
        prefix = section[0]
        n = 0
        profile = self.read_effective_profile() if self.is_project else self.read_profile()
        for item in profile[section]:
            pid = str(item.get("id", ""))
            if pid.startswith(prefix):
                n = max(n, _num_suffix(pid))
        for rec in _iter_jsonl(self.archive_path):
            pid = str(rec.get("id", ""))
            if pid.startswith(prefix) and rec.get("section", section) == section:
                n = max(n, _num_suffix(pid))
        return f"{prefix}{n + 1}"

    def _find_profile_item(self, profile: dict, pid: str) -> tuple[str, dict] | None:
        for s in SECTIONS:
            for item in profile[s]:
                if item.get("id") == pid:
                    return s, item
        return None

    # ------------------------------------------------------------ session
    def active_sids(self) -> list[str]:
        active = self.home / "session" / "active"
        if not active.is_dir():
            return []
        found: list[str] = []
        for path in sorted(active.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            sid = value.get("sid") if isinstance(value, dict) else None
            if isinstance(sid, str) and sid and sid not in found:
                found.append(sid)
        return found

    def current_sid(self) -> str | None:
        active = self.active_sids()
        if len(active) == 1:
            return active[0]
        if len(active) > 1:
            return None
        try:
            s = (self.home / "session" / "current").read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return s or None

    def set_current_sid(self, sid: str) -> None:
        sid = sid.strip()
        if not sid:
            raise UserError("session idが空です")
        digest = hashlib.sha256(sid.encode("utf-8")).hexdigest()
        self.write_text(f"session/active/{digest}.json", dumps({"sid": sid, "updated": now_iso()}) + "\n")
        active = self.active_sids()
        if len(active) == 1:
            self.write_text("session/current", active[0] + "\n")
        else:
            (self.home / "session" / "current").unlink(missing_ok=True)

    def clear_current_sid(self, sid: str | None = None) -> None:
        if sid is None:
            active = self.home / "session" / "active"
            if active.is_dir():
                for path in active.glob("*.json"):
                    path.unlink(missing_ok=True)
        else:
            digest = hashlib.sha256(sid.strip().encode("utf-8")).hexdigest()
            (self.home / "session" / "active" / f"{digest}.json").unlink(missing_ok=True)
        active_sids = self.active_sids()
        current = self.home / "session" / "current"
        if len(active_sids) == 1:
            self.write_text("session/current", active_sids[0] + "\n")
        else:
            current.unlink(missing_ok=True)

    def effective_sid(self) -> str:
        if self.sid:
            return self.sid
        active = self.active_sids()
        if len(active) > 1:
            raise UserError("複数sessionが有効です。混線を防ぐため--sid <session>を指定してください")
        return (active[0] if active else self.current_sid()) or "nosession"

    def workspace(self) -> str:
        """The session's opened folder, independent of an individual tool's working directory."""
        path = f"session/{_safe_name(self.effective_sid())}.workspace"
        value = self.read_text(path)
        if value is not None:
            return value.strip()  # an unknown hook cwd is explicitly empty; do not guess
        return str(Path.cwd().resolve())  # standalone CLI before a session-start hook

    def set_workspace(self, cwd: str) -> None:
        """Record only an absolute host-provided project folder; missing cwd stays unknown."""
        path = Path(cwd) if cwd and not any(ch in cwd for ch in "\r\n") else None
        value = str(path.resolve()) if path is not None and path.is_absolute() else ""
        self.write_text(f"session/{_safe_name(self.effective_sid())}.workspace", value + "\n")

    def set_environment(self, env: str) -> None:
        self.write_text(f"session/{_safe_name(self.effective_sid())}.env", env)

    def environment(self) -> str | None:
        return self.read_text(f"session/{_safe_name(self.effective_sid())}.env")

    def record_user_input(self, prompt: str) -> None:
        from core.ctx import evidence as authority
        previous = self.user_input()
        short = prompt.strip().rstrip("。！!？? ")
        status_only = bool(re.fullmatch(r"がんば(?:れ|って)?|頑張(?:れ|って)|ありがとう(?:ございます)?|いける|進捗(?:は)?|どうなった", short))
        continuation = short in ("再開", "続けて") and previous and not authority.cancels(previous.get("prompt", ""))
        if previous and previous.get("workspace") == self.workspace() and (status_only or continuation):
            rec = {**previous, "latest_prompt": prompt}
        else:
            rec = {"id": secrets.token_hex(12), "prompt": prompt, "latest_prompt": prompt, "workspace": self.workspace()}
        self.write_text(f"session/{_safe_name(self.effective_sid())}.user.json", dumps(rec))
        self.append_event({"type": "user_input", "user_input_id": rec["id"], "chars": len(prompt),
                           "instruction_changed": not previous or rec["id"] != previous.get("id")})

    def user_input(self) -> dict | None:
        raw = self.read_text(f"session/{_safe_name(self.effective_sid())}.user.json")
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return None

    # ------------------------------------------------------------ events
    def _next_seq(self, sid: str) -> int:
        p = self.home / "session" / f"{_safe_name(sid)}.seq"
        try:
            n = int(p.read_text(encoding="utf-8").strip() or 0)
        except (OSError, ValueError):
            n = 0
        n += 1
        _atomic_write(p, str(n))
        return n

    def append_event(self, event: dict) -> str:
        t = event.get("type")
        if t not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {t!r}")
        sid = event.get("sid") or self.effective_sid()
        self._ensure_home()
        with _locked_append(self.events_path) as f:
            seq = self._next_seq(sid)
            rec = {"ts": event.get("ts") or now_iso(), "sid": sid, "seq": seq, "type": t}
            for k, v in event.items():
                if k not in rec:
                    rec[k] = v
            f.write(dumps(rec) + "\n")
        return f"ev:{sid}:{seq}"

    def iter_events(self, since_days: int | None = None, types: set[str] | None = None,
                    sid: str | None = None) -> Iterator[dict]:
        cutoff = None
        if since_days is not None:
            cutoff = _dt.datetime.now().astimezone() - _dt.timedelta(days=since_days)
        for ev in _iter_jsonl(self.events_path):
            if types is not None and ev.get("type") not in types:
                continue
            if sid is not None and ev.get("sid") != sid:
                continue
            if cutoff is not None:
                ts = parse_ts(ev.get("ts"))
                if ts is None or ts < cutoff:
                    continue
            yield ev

    def event_by_id(self, ev_id: str) -> dict | None:
        parsed = parse_event_id(ev_id)
        if parsed is None:
            return None
        sid, seq = parsed
        for ev in self.iter_events(sid=sid):
            if ev.get("seq") == seq:
                return ev
        return None

    def last_event(self, types: set[str] | None = None, sid: str | None = None,
                   tool: str | None = None) -> dict | None:
        found = None
        for ev in self.iter_events(types=types, sid=sid):
            if tool is not None and str(ev.get("tool", "")).lower() != tool.lower():
                continue
            found = ev
        return found

    # ------------------------------------------------------------ candidates
    def _read_candidates(self) -> dict[str, dict]:
        """id → latest record, ordered by first appearance."""
        out: dict[str, dict] = {}
        for rec in _iter_jsonl(self.candidates_path):
            cid = rec.get("id")
            if isinstance(cid, str):
                out[cid] = rec
        return out

    def candidates(self, status: str | None = None) -> list[dict]:
        recs = list(self._read_candidates().values())
        if status is not None:
            recs = [r for r in recs if r.get("status") == status]
        return recs

    def append_candidate(self, cand: dict) -> str:
        kind = cand.get("kind") or "preference"
        if kind not in CANDIDATE_KINDS:
            raise UserError(f"候補の種別は {'/'.join(CANDIDATE_KINDS)} のいずれかです: {kind}")
        text = redact((cand.get("text") or "").strip())
        if not text:
            raise UserError("候補の本文が空です")
        source = cand.get("source") or "inference"
        if not (source in ("user-stated", "inference") or source.startswith("document:")):
            raise UserError(f"候補の source は user-stated / inference / document:<ref> のいずれかです: {source}")
        existing = self._read_candidates()
        workspace = self.workspace()
        for rec in existing.values():
            if (rec.get("status") == "pending" and rec.get("text") == text
                    and rec.get("workspace") == workspace and rec.get("kind") == kind):
                return rec["id"]
        n = max([_num_suffix(cid) for cid in existing] + [0]) + 1
        rec = {
            "id": f"cand-{n}",
            "kind": kind,
            "text": text,
            "quote": redact((cand.get("quote") or text).strip()),
            "source": source,
            "status": "pending",
            "created": now_iso(),
            "sid": self.effective_sid(),
            "scope": "workspace",
            "workspace": workspace,
        }
        if cand.get("key"):
            rec["key"] = str(cand["key"])
        self._ensure_home()
        _append_jsonl(self.candidates_path, rec)
        self.append_event({"type": "candidate", "cid": rec["id"], "kind": kind, "source": source})
        return rec["id"]

    def set_candidate_status(self, cid: str, status: str, reason: str | None = None) -> None:
        if status not in CANDIDATE_STATUSES:
            raise UserError(f"候補の状態は {'/'.join(CANDIDATE_STATUSES)} のいずれかです: {status}")
        recs = self._read_candidates()
        if cid not in recs:
            raise UserError(f"候補がありません: {cid}")
        rec = dict(recs[cid])
        rec["status"] = status
        rec["updated"] = now_iso()
        if reason:
            rec["reason"] = reason
        self._ensure_home()
        _append_jsonl(self.candidates_path, rec)

    def _pending_candidate(self, cid: str) -> dict:
        cand = self._read_candidates().get(cid)
        if cand is None:
            raise UserError(f"候補がありません: {cid}")
        if cand.get("status") != "pending":
            raise UserError(f"候補 {cid} は {cand.get('status')} です（pending の候補だけ処理できます）")
        return cand

    def approve(self, cid: str, confidence: float | None = None, review_by: str | None = None,
                supersedes: str | None = None, *, global_scope: bool = False, quote: str | None = None) -> str:
        cand = self._read_candidates().get(cid)
        if not cand or cand.get("status") == "rejected":
            self._pending_candidate(cid)
        if global_scope:
            from core.ctx import evidence as authority
            authority.global_memory(self, quote, cand["text"])
        elif quote is not None:
            from core.ctx import evidence as authority
            authority.user_quote(self, quote)
        target_store = self.global_store() if global_scope else self
        journal_path = f"approvals/{_safe_name(cid)}.json"
        raw_journal = self.read_text(journal_path)
        if raw_journal:
            journal = json.loads(raw_journal)
            current = target_store._find_profile_item(target_store.read_profile(), journal["pid"])
            if current and current[1].get("candidate_id") == cid:
                self._finish_approval(journal)
                return journal["pid"]
        cand = self._pending_candidate(cid)
        section = KIND_TO_SECTION.get(str(cand.get("kind")))
        if section is None:
            raise UserError(f"候補の種別が不正です: {cand.get('kind')}")
        src = str(cand.get("source") or "inference")
        if src == "user-stated":
            psrc, conf = "user-stated", 1.0
        elif src == "inference":
            psrc, conf = "approved-inference", 0.7
        elif src.startswith("document:"):
            psrc, conf = src, 0.9
        else:
            raise UserError(f"候補の source が不正です: {src}")
        if confidence is not None:
            if not (0.1 <= float(confidence) <= 1.0):
                raise UserError("--confidence は 0.1 から 1.0 の間で指定してください")
            conf = float(confidence)
        rb = parse_date(review_by) if review_by else today() + _dt.timedelta(days=DEFAULT_REVIEW_DAYS[section])
        target_store = self.global_store() if global_scope else self
        profile = target_store.read_profile()
        old = None
        if supersedes:
            old = target_store._find_profile_item(profile, supersedes)
            if old is None:
                raise UserError(f"退役させる項目がありません: {supersedes}")
            if old[1].get("scope", "global") == "global" and not global_scope:
                raise UserError("共通の記憶は案件内の変更で置き換えません。案件の例外は --supersedes なしで追加してください")
            if old[1].get("scope") == "workspace" and old[1].get("workspace") != self.workspace():
                raise UserError("他の案件の記憶は、この案件から置き換えません")
        pid = target_store.new_profile_id(section)
        item: dict = {
            "id": pid,
            "text": cand["text"],
            "source": psrc,
            "recorded_at": today(),
            "confidence": conf,
            "review_by": rb,
            "scope": "global" if global_scope else "workspace",
            "workspace": "" if global_scope else (cand.get("workspace") or self.workspace()),
            "candidate_id": cid,
        }
        key = cand.get("key") or (old[1].get("key") if old else None)
        if key:
            item["key"] = key
        if old:
            item["corrected_from"] = old[1]["id"]
        if section == "goals":
            item["status"] = "active"
        if old:
            old_section, old_item = old
            profile[old_section] = [x for x in profile[old_section] if x.get("id") != old_item["id"]]
        profile[section].append(item)
        # validate → snapshot → os.replace. Nothing below runs when this fails, so the archive never
        # claims an item retired while it is still live in profile.toml.
        journal = {"cid": cid, "pid": pid, "item": item, "old": old, "quote": cand.get("quote"),
                   "global_scope": global_scope, "approval_quote": redact(quote) if quote else None,
                   "user_input_id": (self.user_input() or {}).get("id") if quote else None}
        self.write_text(journal_path, dumps(journal))
        target_store.write_profile(profile)
        self._finish_approval(journal)
        return pid

    def _finish_approval(self, journal: dict) -> None:
        """Resume the single-writer commit tail after I/O failure, without duplicating memory/history."""
        cid, pid, item, old = (journal[k] for k in ("cid", "pid", "item", "old"))
        target_store = self.global_store() if journal.get("global_scope") else self
        transaction_id = f"{cid}:{pid}"
        if old:
            old_section, old_item = old
            arch = dict(old_item)
            arch["section"] = old_section
            arch["superseded_by"] = pid
            arch["superseded_at"] = now_iso()
            if not any(rec.get("id") == old_item["id"] and rec.get("superseded_by") == pid
                       for rec in _iter_jsonl(target_store.archive_path)):
                _append_jsonl(target_store.archive_path, arch)
            if not any(ev.get("transaction_id") == transaction_id for ev in self.iter_events(types={"correction"})):
                self.append_event({"type": "correction", "before": redact(str(old_item.get("text", ""))),
                                   "after": redact(item["text"]), "quote": journal.get("quote"),
                                   "transaction_id": transaction_id})
        self.set_candidate_status(cid, "approved")
        if not any(ev.get("cid") == cid and ev.get("pid") == pid for ev in self.iter_events(types={"approval"})):
            self.append_event({"type": "approval", "cid": cid, "pid": pid, "action": "approve",
                               "quote": journal.get("approval_quote"), "user_input_id": journal.get("user_input_id")})
        (self.home / f"approvals/{_safe_name(cid)}.json").unlink(missing_ok=True)

    def reject(self, cid: str, reason: str | None = None) -> None:
        self._pending_candidate(cid)
        self.set_candidate_status(cid, "rejected", reason)
        self.append_event({"type": "approval", "cid": cid, "pid": None, "action": "reject"})

    def remember(self, text: str, kind: str = "preference", key: str | None = None,
                 *, global_scope: bool = False, quote: str | None = None) -> str:
        """Direct profile write by the user (source user-stated, confidence 1.0); no candidate step."""
        text = redact((text or "").strip())
        if not text:
            raise UserError("記憶する本文が空です")
        if global_scope:
            from core.ctx import evidence as authority
            authority.global_memory(self, quote, text)
        section = KIND_TO_SECTION.get(kind)
        if section is None:
            raise UserError(f"種別は {'/'.join(CANDIDATE_KINDS)} のいずれかです: {kind}")
        target_store = self.global_store() if global_scope else self
        profile = target_store.read_profile()
        pid = target_store.new_profile_id(section)
        item: dict = {
            "id": pid,
            "text": text,
            "source": "user-stated",
            "recorded_at": today(),
            "confidence": 1.0,
            "review_by": today() + _dt.timedelta(days=DEFAULT_REVIEW_DAYS[section]),
            "scope": "global" if global_scope else "workspace",
            "workspace": "" if global_scope else self.workspace(),
        }
        if key:
            item["key"] = str(key)
        if section == "goals":
            item["status"] = "active"
        profile[section].append(item)
        target_store.write_profile(profile)
        self.append_event({"type": "approval", "cid": None, "pid": pid, "action": "approve",
                           "quote": redact(quote) if quote else None,
                           "user_input_id": (self.user_input() or {}).get("id") if quote else None})
        return pid

    def capture(self, text: str, source: str | None = None) -> str:
        text = redact((text or "").strip())
        if not text:
            raise UserError("記録する本文が空です")
        m = re.match(r"https?://\S+", text)  # argument starts with a URL: url = that token, text = whole argument
        url = m.group(0) if m else None
        if url and not source:
            source = f"document:{url}"
        return self.append_event({"type": "capture", "text": text, "source": source, "url": url})

    # ------------------------------------------------------------ tasks / text
    def task_path(self, id: str) -> Path:
        return self.home / "tasks" / f"{id}.md"

    def list_tasks(self) -> list[str]:
        d = self.home / "tasks"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.md") if p.is_file())

    def read_text(self, rel: str) -> str | None:
        p = self.home / rel
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8")

    def write_text(self, rel: str, text: str) -> None:
        self._ensure_home()
        _atomic_write(self.home / rel, text)

    # ------------------------------------------------------------ validation
    def validate(self, kind: Literal["profile", "event", "candidate", "task"], obj: dict) -> list[str]:
        """Return schema errors; profile schema 2 also validates its persona contract."""
        errors: list[str] = []
        if kind not in _SCHEMA_FILES:
            return [f"unknown schema kind: {kind}"]
        if not isinstance(obj, dict):
            return [f"{kind}: オブジェクトではありません"]
        top, item_schema = _schema_tables(kind, str(REPO_ROOT))
        _check_obj(top, obj, "", errors)
        if kind == "profile":
            schema_version = obj.get("schema")
            if isinstance(schema_version, int) and not isinstance(schema_version, bool):
                if schema_version not in (1, 2):
                    errors.append(f"schema: 未対応の版です（{schema_version}）")
                if schema_version == 2 and not isinstance(obj.get("persona"), dict):
                    errors.append("persona: schema 2 の必須キーがありません")
                if schema_version == 1 and "persona" in obj:
                    errors.append("persona: schema 2 でのみ使用できます")
            if isinstance(obj.get("persona"), dict):
                try:
                    from core.ctx.persona import validate_persona
                    validate_persona(obj["persona"])
                except UserError as exc:
                    errors.append(str(exc))
            for s in SECTIONS:
                items = obj.get(s)
                if not isinstance(items, list):
                    continue
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append(f"{s}[{i}]: オブジェクトではありません")
                        continue
                    _check_obj(item_schema, item, f"{s}[{i}].", errors)
        elif kind == "task":
            crits = obj.get("criteria")
            if isinstance(crits, list):
                for i, c in enumerate(crits):
                    if not isinstance(c, dict):
                        errors.append(f"criteria[{i}]: オブジェクトではありません")
                        continue
                    _check_obj(item_schema, c, f"criteria[{i}].", errors)
        return errors
