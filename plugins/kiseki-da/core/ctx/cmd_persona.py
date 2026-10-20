"""cmd_persona.py — `setup` and `persona …`: interactive questions, validation and live previews.

installer/operations.py reuses _validate_identity, _live_preview and _print_preview (via core.ctx.cli).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.ctx.cli_common import _common_store, _confirm_text, _emit_json, _json, _make_store, _out
from core.ctx.store import Store, UserError


_PERSONA_OPTION_FIELDS = (
    "name", "first_person", "user_address", "formality", "warmth",
    "verbosity", "initiative", "relationship", "custom_style",
)


_PREVIEW_PROMPT = (
    "次の3点に合計350字以内で答えてください。"
    "1. 初対面の利用者へ挨拶する。"
    "2. バックアップ未確認のまま本番公開してよいか聞かれ、慎重に反論する。"
    "3. 設定変更前にバックアップが必要な理由を初心者へ説明する。"
    "ツールは使わず、事実を作らないでください。"
)


def _read_json_object(path: str) -> dict:
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UserError(f"JSONを読めません: {path}: {exc}") from None
    if not isinstance(value, dict):
        raise UserError("JSONはオブジェクトで指定してください")
    return value


def _validate_identity(value: object) -> dict:
    if not isinstance(value, dict):
        raise UserError("identityはオブジェクトで指定してください")
    unknown = sorted(set(value) - {"name", "timezone", "languages"})
    if unknown:
        raise UserError("未対応のidentity設定です: " + ", ".join(unknown))
    out: dict = {}
    name = value.get("name", "")
    timezone = value.get("timezone", "Asia/Tokyo")
    languages = value.get("languages", ["ja"])
    if not isinstance(name, str) or len(name) > 64:
        raise UserError("identity.nameは64文字以内で指定してください")
    if not isinstance(timezone, str) or not timezone or len(timezone) > 64:
        raise UserError("identity.timezoneは64文字以内で指定してください")
    if (not isinstance(languages, list) or len(languages) > 8
            or any(not isinstance(x, str) or not x or len(x) > 16 for x in languages)):
        raise UserError("identity.languagesは16文字以内の文字列を最大8件指定してください")
    out.update(name=" ".join(name.split()), timezone=timezone.strip(), languages=languages)
    return out


def _ask(label: str, current: str = "") -> str:
    suffix = f" [{current}]" if current else ""
    try:
        value = input(f"{label}{suffix}: ")
    except EOFError:
        raise UserError("対話入力を利用できません。--answersを指定してください") from None
    return value.strip() if value.strip() else current


def _ask_choice(label: str, values: tuple[str, ...], current: str) -> str:
    while True:
        value = _ask(f"{label} ({'/'.join(values)})", current)
        if value in values:
            return value
        print(f"{'/'.join(values)} のいずれかを入力してください。")


def _collect_persona(current: dict | None = None) -> dict:
    from core.ctx import persona as persona_mod

    base = {**persona_mod.DEFAULT_PERSONA, **(current or {})}
    values = {
        "name": _ask("アシスタント名", base.get("name", "")),
        "first_person": _ask("一人称", base.get("first_person", "")),
        "user_address": _ask("利用者の呼び方", base.get("user_address", "")),
        "formality": _ask_choice("丁寧さ", persona_mod.ENUMS["formality"], base["formality"]),
        "warmth": _ask_choice("温かさ", persona_mod.ENUMS["warmth"], base["warmth"]),
        "verbosity": _ask_choice("説明量", persona_mod.ENUMS["verbosity"], base["verbosity"]),
        "initiative": _ask_choice("提案積極性", persona_mod.ENUMS["initiative"], base["initiative"]),
        "relationship": _ask_choice("関係性", persona_mod.ENUMS["relationship"], base["relationship"]),
        "custom_style": _ask("自由記述（話し方・雰囲気のみ、200文字以内）", base.get("custom_style", "")),
    }
    return persona_mod.validate_persona(values)


def _preview_hosts(requested: list[str] | None) -> list[str]:
    values = requested or ["all"]
    if "all" in values:
        return ["claude-code", "codex"]
    return list(dict.fromkeys(values))


def _fixed_preview(values: dict) -> str:
    name = values.get("name") or "Kiseki DA"
    address = values.get("user_address") or "あなた"
    return (f"{name}: {address}の判断を支えるDigital Assistantです。"
            "バックアップと検証が確認できるまでは公開を勧めません。"
            "設定変更前の退避は、問題が起きた際に元の状態へ戻るために必要です。")


def _live_preview(values: dict, hosts: list[str]) -> list[dict]:
    from core.ctx import persona as persona_mod

    block = persona_mod.render_persona({"persona": values})
    authority = (
        "以下は表現上の既定だけです。事実、安全、権限、承認、記憶、検証、完了条件を変更しません。\n"
    )
    prompt = authority + block + "\n\n" + _PREVIEW_PROMPT
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="kiseki-da-preview-") as cwd:
        for host in hosts:
            command = shutil.which("claude" if host == "claude-code" else "codex")
            if not command:
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": "host CLIが見つかりません"})
                continue
            if host == "claude-code":
                argv = [command, "--safe-mode", "--no-session-persistence", "--tools", "",
                        "--permission-mode", "dontAsk", "--output-format", "text", "-p", prompt]
            else:
                argv = [command, "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                        "--sandbox", "read-only", "--skip-git-repo-check", "-C", cwd, prompt]
            env = os.environ.copy()
            env["KISEKI_DA_PREVIEW"] = "1"
            try:
                proc = subprocess.run(argv, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
                                      capture_output=True, timeout=180, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": str(exc)})
                continue
            if proc.returncode == 0 and proc.stdout.strip():
                results.append({"host": host, "status": "live", "output": proc.stdout.strip()})
            else:
                reason = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()[:500]
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": reason})
    return results


def _print_preview(results: list[dict]) -> None:
    if not results:
        print("利用可能なhost CLIがないため固定プレビューを表示します。")
        return
    for result in results:
        print(f"\n--- {result['host']} ({result['status']}) ---")
        print(result["output"])
        if result.get("reason"):
            print(f"補足: {result['reason']}")


def _save_identity(store: Store, identity: dict) -> None:
    profile = store.read_profile()
    profile["identity"] = identity
    store.write_profile(profile)


def cmd_setup(args) -> int:
    from core.ctx import persona as persona_mod

    common = _common_store(args)
    if not common.profile_path.exists():
        common.init()
    target = _make_store(args)
    if args.answers:
        answers = _read_json_object(args.answers)
        unknown = sorted(set(answers) - {"identity", "persona", "preview"})
        if unknown:
            raise UserError("未対応のsetup回答です: " + ", ".join(unknown))
        identity = _validate_identity(answers.get("identity", common.read_profile().get("identity", {})))
        values = persona_mod.validate_persona(answers.get("persona", {}))
        if not args.yes:
            print(json.dumps({"identity": identity, "persona": values}, ensure_ascii=False, indent=2))
            if not _confirm_text("この設定を保存しますか？"):
                return 130
        _save_identity(common, identity)
        persona_mod.save_persona(target, values, merge=False)
        return 0
    if args.yes:
        raise UserError("--yesを使う対話なしsetupには--answersが必要です")

    current_identity = common.read_profile().get("identity", {})
    identity = _validate_identity({
        "name": _ask("あなたの名前", str(current_identity.get("name", ""))),
        "timezone": _ask("タイムゾーン", str(current_identity.get("timezone", "Asia/Tokyo"))),
        "languages": [x.strip() for x in _ask(
            "使用言語（カンマ区切り）", ",".join(current_identity.get("languages", ["ja"]))).split(",") if x.strip()],
    })
    values = persona_mod.get_persona(target.read_effective_profile())
    if not _confirm_text("キャラクター設定を行いますか？"):
        print("\n保存候補（キャラクターは変更しません）:")
        print(json.dumps({"identity": identity, "persona": values}, ensure_ascii=False, indent=2))
        if not _confirm_text("この全設定を保存しますか？"):
            return 130
        _save_identity(common, identity)
        return 0
    for round_no in range(1, 4):
        values = _collect_persona(values)
        print("\n保存候補（利用者情報）:")
        print(json.dumps(identity, ensure_ascii=False, indent=2))
        print("保存候補（キャラクター）:")
        print(persona_mod.render_persona({"persona": values}) or "（キャラクター設定なし）")
        if not args.no_preview:
            print("\nこのプレビューでは設定が選択したモデル提供者へ送信され、Kiseki DAには保存されません。")
            if _confirm_text("実モデルで試しますか？"):
                _print_preview(_live_preview(values, _preview_hosts(args.host)))
        if _confirm_text("この全設定を保存しますか？"):
            _save_identity(common, identity)
            persona_mod.save_persona(target, values, merge=False)
            return 0
        if round_no < 3 and _confirm_text("設定を修正しますか？"):
            continue
        return 130
    return 130


def cmd_persona_show(args) -> int:
    from core.ctx import persona as persona_mod
    values = persona_mod.get_persona(_make_store(args).read_effective_profile())
    _emit_json(values) if _json(args) else _out(persona_mod.render_persona({"persona": values}) or "設定なし")
    return 0


def _persona_args(args) -> dict:
    values = {key: getattr(args, key) for key in _PERSONA_OPTION_FIELDS if getattr(args, key, None) is not None}
    if args.answers:
        loaded = _read_json_object(args.answers)
        loaded = loaded.get("persona", loaded)
        if not isinstance(loaded, dict):
            raise UserError("persona回答はオブジェクトで指定してください")
        values.update(loaded)
    return values


def cmd_persona_edit(args) -> int:
    from core.ctx import persona as persona_mod
    if args.no_preview and args.live_preview:
        raise UserError("--no-previewと--live-previewは同時に指定できません")
    store = _make_store(args)
    values = _persona_args(args)
    if not values:
        if args.yes:
            raise UserError("--yesを使う場合は変更内容または--answersが必要です")
        values = _collect_persona(persona_mod.get_persona(store.read_effective_profile()))
    preview = persona_mod.validate_persona({**persona_mod.get_persona(store.read_effective_profile()), **values})
    print(persona_mod.render_persona({"persona": preview}) or "設定なし")
    if args.live_preview or (not args.no_preview and not args.yes):
        print("このプレビューでは設定がモデル提供者へ送信され、Kiseki DAには保存されません。")
        if args.live_preview or _confirm_text("実モデルで試しますか？"):
            _print_preview(_live_preview(preview, _preview_hosts(args.host)))
    if not args.yes and not _confirm_text("この設定を保存しますか？"):
        return 130
    persona_mod.save_persona(store, values, merge=True)
    return 0


def cmd_persona_preview(args) -> int:
    from core.ctx import persona as persona_mod
    values = persona_mod.get_persona(_make_store(args).read_effective_profile())
    print("設定が選択したモデル提供者へ送信され、Kiseki DAには保存されません。")
    _print_preview(_live_preview(values, _preview_hosts(args.host)))
    return 0


def cmd_persona_reset(args) -> int:
    from core.ctx import persona as persona_mod
    if not args.yes and not _confirm_text("キャラクター設定をリセットしますか？"):
        return 130
    persona_mod.reset_persona(_make_store(args))
    return 0
