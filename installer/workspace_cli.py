"""Public project generation and on-demand pack operations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .constants import SOURCE_ROOT
from .util import InstallerError


def handles(argv):
    argv = _without_sid(argv)
    return bool(argv) and (argv[0] in {"skills", "access"} or
        argv[:2] in (["project", "create"], ["project", "show"], ["project", "recover"],
                    ["project", "refresh-guidance"], ["persona", "pack"]))


def _without_sid(argv):
    stripped = []
    it = iter(argv)
    for arg in it:
        if arg == "--sid":
            if next(it, None) is None:
                raise InstallerError("--sid の値がありません。")
        elif not arg.startswith("--sid="):
            stripped.append(arg)
    return stripped


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InstallerError("引数が不正です: " + message)


def _json_file(value):
    try:
        return json.loads(Path(value).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallerError(f"JSONを読めません: {exc}") from None


def main(argv, source=SOURCE_ROOT):
    from . import packs, projects
    parser = Parser(prog="kiseki-da")
    commands = parser.add_subparsers(dest="command", required=True)
    access = commands.add_parser("access", help="この実行環境から保存先へ書き込めるか診断する")
    access.add_argument("--json", action="store_true")
    project = commands.add_parser("project").add_subparsers(dest="action", required=True)
    create = project.add_parser("create", help="固定版基盤付きの作業環境を作成する")
    create.add_argument("destination")
    create.add_argument("--answers", help="name/goal/scope/persona/skills/context/source_task/roleのJSON")
    create.add_argument("--name")
    create.add_argument("--goal")
    create.add_argument("--scope")
    create.add_argument("--persona")
    create.add_argument("--skills", nargs="+")
    create.add_argument("--context", help="text/source/dateの配列JSON")
    create.add_argument("--source-task")
    create.add_argument("--role", choices=("main", "child"))
    create.add_argument("--dry-run", action="store_true")
    for action in ("show", "recover"):
        project.add_parser(action).add_argument("destination")
    refresh = project.add_parser("refresh-guidance", help="既存案件の文脈・CLI案内の更新をプレビューする")
    refresh.add_argument("destination")
    refresh.add_argument("--apply", action="store_true")
    skill = commands.add_parser("skills").add_subparsers(dest="action", required=True)
    listing = skill.add_parser("list")
    listing.add_argument("query", nargs="?", default="")
    skill.add_parser("show").add_argument("name")
    export = skill.add_parser("export")
    export.add_argument("name")
    export.add_argument("destination")
    activate = skill.add_parser("main")
    activate.add_argument("destination", help="18スキルの配置先ディレクトリ")
    migrate = skill.add_parser("migrate")
    migrate.add_argument("--visible", required=True)
    migrate.add_argument("--archive", required=True)
    migrate.add_argument("--apply", action="store_true")
    persona = commands.add_parser("persona").add_subparsers(dest="action", required=True)
    preset = persona.add_parser("pack")
    preset.add_argument("name", nargs="?")
    # The session argument is accepted for consistency; this extension does not
    # manufacture runtime events or replace the host's evidence recorder.
    args = parser.parse_args(_without_sid(argv))
    if args.command == "access":
        from .runtime_access import check_access
        from .util import kiseki_home
        result = check_access(kiseki_home())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "writable" else 2
    if args.command == "project":
        if args.action == "create":
            values = _json_file(args.answers) if args.answers else {}
            allowed = {"name", "goal", "scope", "persona", "skills", "context", "source_task", "role"}
            if not isinstance(values, dict) or set(values) - allowed:
                raise InstallerError("project answersの項目が不正です。")
            for field in allowed - {"context"}:
                value = getattr(args, field)
                if value is not None:
                    values[field] = value
            if args.context:
                values["context"] = _json_file(args.context)
            missing = {"name", "goal", "scope", "persona"} - set(values)
            if missing:
                raise InstallerError("指定が必要です: " + ", ".join(sorted(missing)))
            result = projects.create_project(Path(source), Path(args.destination), dry_run=args.dry_run, **values)
        elif args.action == "show":
            result = projects.show_project(Path(args.destination))
        elif args.action == "refresh-guidance":
            from .project_guidance import refresh_guidance
            result = refresh_guidance(Path(source), Path(args.destination), apply=args.apply)
        else:
            result = projects.recover_project(Path(args.destination))
    elif args.command == "persona":
        result = packs.get_persona(Path(source), args.name) if args.name else packs.list_personas(Path(source))
    elif args.action == "list":
        query = args.query.casefold()
        result = [{k: row[k] for k in ("name", "description", "source", "execution_status")}
                  for row in packs.skill_catalog(Path(source))
                  if query in (row["name"] + " " + row["description"]).casefold()]
    elif args.action == "show":
        rows = {row["name"]: row for row in packs.skill_catalog(Path(source))}
        if args.name not in rows:
            raise InstallerError(f"スキルがありません: {args.name}")
        row = rows[args.name]
        result = {**row, "body": (Path(row["source"]) / "SKILL.md").read_text(encoding="utf-8")}
    elif args.action == "export":
        result = packs.export_skill(Path(source), args.name, Path(args.destination))
    elif args.action == "main":
        result = packs.copy_selected_skills(Path(source), list(packs.MAIN_SKILLS), Path(args.destination))
    else:
        from .skill_migration import migrate_skills
        result = migrate_skills(Path(source), Path(args.visible), Path(args.archive), dry_run=not args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
