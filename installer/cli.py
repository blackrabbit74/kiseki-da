"""Public ``kiseki-da`` command dispatcher."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .constants import HOSTS, PRODUCT, SOURCE_ROOT, VERSION
from .operations import (
    attest_codex_trust,
    describe_plan,
    doctor,
    install,
    rollback,
    runtime_dispatch,
    uninstall,
)
from .update_source import update_source
from .util import InstallerError, kiseki_home, load_answers, verify_checksum


RUNTIME_COMMANDS = {
    "setup", "persona", "project", "task", "search", "candidate", "approve", "reject",
    "remember", "report", "capture", "log", "build", "hook", "evals",
    "verify",
    "session",
}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InstallerError(f"引数が不正です: {message}")


def _parser() -> Parser:
    root = Parser(prog="kiseki-da", description="Kiseki DA — Digital Assistant control plane")
    sub = root.add_subparsers(dest="command")

    p = sub.add_parser("install", help="Claude Code/Codexへtransactional install")
    p.add_argument("--host", choices=(*HOSTS, "all"), default=None)
    p.add_argument("--scope", choices=("user", "project"), default=None)
    p.add_argument("--project", default=None)
    p.add_argument("--answers", default=None, help="非対話セットアップ用JSON")
    p.add_argument("--yes", action="store_true", help="表示した変更を確認済みとして進める")
    p.add_argument("--dry-run", action="store_true", help="書込みを行わず変更予定を表示する")
    p.add_argument("--host-security", choices=("preserve", "recommended"), default=None,
                   help="hostの承認・sandbox設定（既定は変更しない）")
    p.add_argument("--import-legacy", action="store_true", help="検出した旧PA_HOME/~/.paをcopyして移行する")
    p.add_argument("--source", default=None, help=argparse.SUPPRESS)

    sub.add_parser("setup", help="初期設定（インストール後のruntimeへ委譲）")

    p = sub.add_parser("persona", help="キャラクター設定")
    p.add_argument("persona_args", nargs=argparse.REMAINDER)

    p = sub.add_parser("project", help="project scope管理")
    p.add_argument("project_args", nargs=argparse.REMAINDER)

    p = sub.add_parser("doctor", help="導入状態を診断する")
    p.add_argument("--json", action="store_true")
    p.add_argument("--confirm-codex-trust", action="store_true",
                   help="Codex /hooksで現在のhookをtrustしたことを明示記録する")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("update", help="明示的に最新版へ更新する")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--source", default=None, help=argparse.SUPPRESS)

    p = sub.add_parser("rollback", help="transactionを元に戻す")
    p.add_argument("--transaction", default="latest")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("uninstall", help="plugin/runtimeを外す（個人状態は保持）")
    p.add_argument("--host", choices=(*HOSTS, "all"), action="append")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    sub.add_parser("version", help="versionを表示する")

    p = sub.add_parser("verify-release", help=argparse.SUPPRESS)
    p.add_argument("archive")
    p.add_argument("checksum")
    return root


def _emit(value: dict[str, Any], *, json_output: bool = False, show_plan: bool = True) -> None:
    if json_output:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if show_plan and "action" in value:
        print(describe_plan(value))
    if value.get("transaction"):
        print(f"transaction: {value['transaction']}")
    if value.get("status"):
        print(f"status: {value['status']}")
    if value.get("error"):
        print(f"error: {value['error']}", file=sys.stderr)
    rollback_errors = value.get("rollback_errors") or value.get("errors")
    if value.get("status") == "rollback_incomplete":
        if value.get("journal"):
            print(f"journal: {value['journal']}", file=sys.stderr)
        for error in rollback_errors or []:
            print(f"rollback error: {error}", file=sys.stderr)
        if value.get("transaction"):
            print(f"復旧再試行: kiseki-da rollback --transaction {value['transaction']}", file=sys.stderr)


def _confirm() -> bool:
    try:
        answer = input("この内容で実行しますか？ [y/N]: ").strip().casefold()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def _choose(label: str, choices: tuple[str, ...], default: str) -> str:
    """Small Japanese installer prompt; Enter explicitly accepts the shown default."""
    while True:
        try:
            value = input(f"{label} ({'/'.join(choices)}) [{default}]: ").strip()
        except EOFError:
            raise InstallerError("対話入力を利用できません。--answersまたはCLI引数を指定してください。") from None
        value = value or default
        if value in choices:
            return value
        print(f"{ '/'.join(choices) } のいずれかを入力してください。")


def _saved_activation() -> tuple[str | None, list[Path]]:
    """Read the live activation registry; install metadata is only an audit snapshot."""
    try:
        value = json.loads((kiseki_home() / "projects.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, []
    if not isinstance(value, dict) or value.get("mode") not in {"user", "project"}:
        return None, []
    rows = value.get("projects") if isinstance(value.get("projects"), list) else []
    projects = [Path(row["path"]) for row in rows
                if isinstance(row, dict) and isinstance(row.get("path"), str)]
    return str(value["mode"]), projects


def _install_command(args: argparse.Namespace) -> int:
    answers = load_answers(args.answers)
    allowed = {"schema", "host", "hosts", "scope", "project", "activation", "identity", "persona",
               "host_security", "security", "preview", "migration"}
    unknown_answers = sorted(set(answers) - allowed)
    if unknown_answers:
        raise InstallerError("未対応のanswers項目です: " + ", ".join(unknown_answers))
    if args.yes and not args.dry_run and not args.answers:
        raise InstallerError("非対話installの--yesには完全な--answersファイルが必要です。")
    activation = answers.get("activation") if isinstance(answers.get("activation"), dict) else {}
    if "schema" in answers and answers["schema"] != 1:
        raise InstallerError("answers.schemaは1で指定してください。")
    if answers.get("activation") is not None and not isinstance(answers.get("activation"), dict):
        raise InstallerError("answers.activationはJSONオブジェクトで指定してください。")
    if set(activation) - {"mode", "projects"}:
        raise InstallerError("answers.activationに未対応の項目があります。")
    if answers.get("security") is not None and not isinstance(answers.get("security"), dict):
        raise InstallerError("answers.securityはJSONオブジェクトで指定してください。")
    if isinstance(answers.get("security"), dict) and set(answers["security"]) - {"apply_recommended_host_settings"}:
        raise InstallerError("answers.securityに未対応の項目があります。")
    if answers.get("preview") is not None and not isinstance(answers.get("preview"), dict):
        raise InstallerError("answers.previewはJSONオブジェクトで指定してください。")
    if isinstance(answers.get("preview"), dict) and set(answers["preview"]) - {"enabled", "hosts", "max_rounds"}:
        raise InstallerError("answers.previewに未対応の項目があります。")
    preview_answers = answers.get("preview") if isinstance(answers.get("preview"), dict) else {}
    if "enabled" in preview_answers and not isinstance(preview_answers["enabled"], bool):
        raise InstallerError("answers.preview.enabledはtrue/falseで指定してください。")
    if "max_rounds" in preview_answers and (not isinstance(preview_answers["max_rounds"], int)
                                             or not 1 <= preview_answers["max_rounds"] <= 3):
        raise InstallerError("answers.preview.max_roundsは1〜3で指定してください。")
    interactive_choices = not args.yes and not args.dry_run and not args.answers
    selected_host = args.host or answers.get("hosts") or answers.get("host")
    if selected_host is None and interactive_choices:
        selected_host = _choose("導入するhost", ("claude-code", "codex", "all"), "all")
    host = selected_host or "all"
    if isinstance(host, list):
        hosts = host
    else:
        hosts = [str(host)]
    saved_scope, saved_projects = _saved_activation()
    selected_scope = args.scope or activation.get("mode") or answers.get("scope") or saved_scope
    if selected_scope is None and interactive_choices:
        selected_scope = _choose("利用scope", ("user", "project"), "user")
    scope = str(selected_scope or "user")
    project_value = args.project or answers.get("project")
    projects = activation.get("projects") if isinstance(activation, dict) else None
    if projects is not None and (not isinstance(projects, list) or len(projects) > 1
                                 or any(not isinstance(item, dict) for item in projects)):
        raise InstallerError("初回installのactivation.projectsはオブジェクトを最大1件指定してください。")
    if not project_value and isinstance(projects, list) and projects:
        first = projects[0]
        if isinstance(first, dict):
            project_value = first.get("path")
            if "persona" not in answers and isinstance(first.get("persona"), dict):
                answers["persona"] = first["persona"]
    if scope == "project" and not project_value and saved_projects:
        project_value = str(saved_projects[0])
    if scope == "project" and not project_value and interactive_choices:
        try:
            project_value = input(f"対象projectの絶対path [{Path.cwd()}]: ").strip() or str(Path.cwd())
        except EOFError:
            raise InstallerError("project pathを入力できません。--projectを指定してください。") from None
    project = Path(project_value).expanduser() if project_value else None
    source = Path(args.source).expanduser().resolve() if args.source else SOURCE_ROOT
    security_answers = answers.get("security") if isinstance(answers.get("security"), dict) else {}
    recommended = security_answers.get("apply_recommended_host_settings")
    security = args.host_security or str(answers.get("host_security") or
                                         ("recommended" if recommended is True else "preserve"))
    migration = answers.get("migration") if isinstance(answers.get("migration"), dict) else {}
    import_legacy = bool(args.import_legacy or migration.get("import_legacy") is True)
    if args.yes and not args.dry_run:
        if "identity" not in answers or "persona" not in answers:
            raise InstallerError("非対話installのanswersにはidentityとpersonaが必要です。")
    if args.dry_run:
        preview_code, preview = install(hosts=hosts, scope=scope, project=project, answers=answers,
                                        yes=True, dry_run=True, source=source, host_security=security,
                                        import_legacy=import_legacy)
        _emit(preview)
        return preview_code
    preview_code, preview = install(hosts=hosts, scope=scope, project=project, answers=answers,
                                    yes=True, dry_run=True, source=source, host_security=security,
                                    import_legacy=import_legacy, allow_host_probes=True)
    _emit(preview)
    if not args.yes:
        if not _confirm():
            print("中止しました。")
            return 130
    code, result = install(hosts=hosts, scope=scope, project=project, answers=answers,
                           yes=args.yes, dry_run=False, source=source, host_security=security,
                           import_legacy=import_legacy)
    _emit(result, show_plan=False)
    if code == 0:
        print(f"launcher: {kiseki_home() / 'bin' / 'kiseki-da'}")
        if shutil.which("kiseki-da") is None:
            print("注意: kiseki-daがPATHにありません。上記launcherを直接使うか、doctorが示すuser scripts directoryをPATHへ追加してください。")
        if "codex" in hosts:
            print("Codexを再起動し、/hooksでKiseki DA hookをtrustしてください。")
    return code


def _update_command(args: argparse.Namespace) -> int:
    metadata_path = kiseki_home() / "install.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise InstallerError("install metadataを読めません。先にinstallを実行してください。") from None
    hosts = [str(h) for h in metadata.get("hosts", [])]
    saved_scope, _ = _saved_activation()
    scope = saved_scope or str(metadata.get("scope", "user"))
    # Update preserves the complete live registry; it never adds cwd as a side
    # effect just because project mode currently has zero or multiple roots.
    project = None
    security = str(metadata.get("security_settings", "preserve"))
    if args.dry_run and not (args.source or os.environ.get("KISEKI_DA_UPDATE_SOURCE")):
        _emit({
            "action": "update",
            "home": str(kiseki_home()),
            "version": metadata.get("version"),
            "hosts": hosts,
            "scope": scope,
            "project": str(project) if project else None,
            "security_settings": security,
            "status": "dry_run_no_network",
            "network": False,
            "note": "最新版確認とdownloadは実行していません。実行時だけGitHubへ接続します。",
        })
        return 0
    with update_source(args.source) as source:
        if args.dry_run:
            preview_code, preview = install(hosts=hosts, scope=scope, project=project, answers={}, yes=True,
                                            dry_run=True, source=source, update_mode=True,
                                            host_security=security)
            _emit(preview)
            return preview_code
        preview_code, preview = install(hosts=hosts, scope=scope, project=project, answers={}, yes=True,
                                        dry_run=True, source=source, update_mode=True,
                                        host_security=security, allow_host_probes=True)
        _emit(preview)
        if not args.yes:
            if not _confirm():
                print("中止しました。")
                return 130
        code, result = install(hosts=hosts, scope=scope, project=project, answers={}, yes=True,
                               dry_run=False, source=source, update_mode=True, host_security=security)
        _emit(result, show_plan=False)
        return code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["install"]
    if argv and argv[0] in RUNTIME_COMMANDS and argv[0] not in {"setup", "persona", "project"}:
        try:
            return runtime_dispatch(argv)
        except InstallerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    parser = _parser()
    try:
        args, unknown = parser.parse_known_args(argv)
        if args.command is None:
            parser.print_help()
            return 1
        if args.command == "install":
            if unknown:
                raise InstallerError("不明な引数です: " + " ".join(unknown))
            return _install_command(args)
        if args.command == "update":
            if unknown:
                raise InstallerError("不明な引数です: " + " ".join(unknown))
            return _update_command(args)
        if args.command == "doctor":
            if unknown:
                raise InstallerError("不明な引数です: " + " ".join(unknown))
            if args.confirm_codex_trust:
                if not args.yes and not _confirm():
                    print("中止しました。")
                    return 130
                record = attest_codex_trust()
                if not args.json:
                    print(f"Codex hook trust attestation: {record['hook_sha256']}")
            code, result = doctor()
            if args.json:
                _emit(result, json_output=True)
            else:
                print(f"Kiseki DA doctor: {result['status']}")
                for check in result["checks"]:
                    print(f"[{check['status']}] {check['name']}: {check['detail']}")
            return code
        if args.command == "rollback":
            if unknown:
                raise InstallerError("不明な引数です: " + " ".join(unknown))
            if not args.yes and not _confirm():
                print("中止しました。")
                return 130
            code, result = rollback(args.transaction)
            _emit(result, json_output=False)
            return code
        if args.command == "uninstall":
            if unknown:
                raise InstallerError("不明な引数です: " + " ".join(unknown))
            if args.dry_run:
                preview_code, preview = uninstall(hosts=args.host, dry_run=True)
                _emit(preview)
                return preview_code
            preview_code, preview = uninstall(hosts=args.host, dry_run=True, allow_host_probes=True)
            _emit(preview)
            if not args.yes:
                if not _confirm():
                    print("中止しました。")
                    return 130
            code, result = uninstall(hosts=args.host, dry_run=False)
            _emit(result, show_plan=False)
            return code
        if args.command == "version":
            print(VERSION)
            return 0
        if args.command == "verify-release":
            verify_checksum(Path(args.archive).resolve(), args.checksum)
            print("SHA-256: OK")
            return 0
        if args.command == "setup":
            return runtime_dispatch(["setup", *unknown])
        if args.command == "persona":
            return runtime_dispatch(["persona", *args.persona_args, *unknown])
        if args.command == "project":
            return runtime_dispatch(["project", *args.project_args, *unknown])
        raise InstallerError(f"未対応commandです: {args.command}")
    except KeyboardInterrupt:
        print("中断しました。", file=sys.stderr)
        return 130
    except InstallerError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
