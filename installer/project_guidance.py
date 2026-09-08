"""Render compact operating guidance into the existing startup budget."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess

from .util import InstallerError


LEGACY_ENTRY_SHA256 = "78f68216d65cf339ee8062f1a02a703b057bf5f18e78209fad06bd065bdfcc3b"


GUIDANCE = """## 案件文脈の運び方
- 常駐には目的・必須制約・現在の決定・次の一手・詳細の取得先を選ぶ。Kisekiの起動出力全体を推定2500 tokens・9000文字以内に収める。
- 作業ごとに次の判断に必要な情報を特定し、task show / searchで該当部分を取得する。必須制約の省略表示はcontext requiredの全ページで補う。
- 進展したら現在の要点を更新・置換し、資料・理由・履歴・証拠は出典と日付付きで案件の記録に保存する。長期記憶は既存の承認手順で扱う。
- AGENTS.md等の自動読込文書は短い案内と取得先に整え、詳細は必要時に開く。生成・指示更新時はcontext-auditで起動出力と案件直下の指示候補を合算し、超過時は重複を統合・詳細を参照化して再確認する。実読込と測定外の量はホストで確認する。
- 子の生成にもこの手順を引き継ぎ、目的に必要な初期文脈だけを選ぶ。権限エラーは同じCLI操作をホストの権限確認へ戻し、許可後に同じ保存先・引数・--sidで再実行する。
"""


def render_entry(source):
    root = Path(source) / "installer"
    template = (root / "assets/project_entry.py.tmpl").read_text(encoding="utf-8")
    if "__KISEKI_ACCESS_HELPER__" not in template:
        return template  # guidance-refreshed legacy runtime: already self-contained
    helper = (root / "runtime_access.py").read_text(encoding="utf-8")
    return template.replace("__KISEKI_ACCESS_HELPER__", helper).replace("__KISEKI_CONTEXT_GUIDANCE__", repr(GUIDANCE))


def refresh_guidance(source, destination, *, apply=False):
    """Explicit, backed-up update of a known generated beta.8 entry.

Update the frozen template too, so descendants inherit the same procedure.
Core, host configuration, task history and memory remain byte-for-byte intact.
"""
    from .projects import _reject_symlink_ancestors, _tree_digest
    from .transaction import Transaction

    destination = Path(destination).expanduser().absolute()
    _reject_symlink_ancestors(destination)
    destination = destination.resolve()
    base = destination / ".kiseki"
    runtime = base / "runtime"
    entry = base / "entry.py"
    template = runtime / "installer/assets/project_entry.py.tmpl"
    manifest_path = base / "project.json"
    for path in (entry, template, manifest_path, base / "transactions"):
        _reject_symlink_ancestors(path, destination)
    try:
        before = {path: path.read_bytes() for path in (entry, template, manifest_path)}
        manifest = json.loads(before[manifest_path])
    except (OSError, ValueError) as exc:
        raise InstallerError(f"生成済み案件を確認できません: {exc}") from None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("runtime"), dict):
        raise InstallerError("案件manifestのruntimeが不正です。")
    updated = render_entry(source)
    digest = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    old_digest = hashlib.sha256(before[entry]).hexdigest()
    plan = {"action": "project-refresh-guidance", "destination": str(destination),
            "before": old_digest, "after": digest, "guidance": GUIDANCE,
            "targets": [str(path) for path in before]}
    original_runtime_digest = _tree_digest(runtime)
    if original_runtime_digest != manifest["runtime"].get("sha256"):
        raise InstallerError("固定runtimeのhashが一致しません。既存変更を個別確認してください。")
    if old_digest == digest:
        if render_entry(runtime) != updated:
            raise InstallerError("子孫への生成用テンプレートが一致しません。差分を個別確認してください。")
        return {**plan, "status": "unchanged"}
    if (manifest["runtime"].get("version") != "0.1.0-beta.8"
            or old_digest != LEGACY_ENTRY_SHA256 or before[template] != before[entry]):
        raise InstallerError("既知の未変更beta.8入口と一致しません。差分を個別確認してください。")
    if not apply:
        return {**plan, "status": "preview"}
    tx = Transaction(base, "project-refresh-guidance", preserve_user_state_on_manual=True)
    try:
        if any(path.read_bytes() != content for path, content in before.items()):
            raise InstallerError("プレビュー後に案件が変更されました。再確認してください。")
        if _tree_digest(runtime) != original_runtime_digest:
            raise InstallerError("固定runtimeが変更されました。再確認してください。")
        tx.write_text(entry, updated, mode=0o600)
        tx.write_text(template, updated, mode=0o600)
        manifest["runtime"]["sha256"] = _tree_digest(runtime)
        manifest["guidance_update"] = {
            "at": dt.datetime.now(dt.timezone.utc).isoformat(), "transaction": tx.id,
            "entry_sha256": digest, "previous_entry_sha256": old_digest,
            "previous_runtime_sha256": original_runtime_digest,
        }
        tx.write_json(manifest_path, manifest, mode=0o600)
        tx.commit(entry_sha256=digest)
        return {**plan, "status": "updated", "transaction": tx.id,
                "backup": str(tx.root), "next": "次のセッションでホストが要求する信頼確認を行い、起動文脈とaccessを確認してください。"}
    except BaseException as exc:
        ok = tx.rollback(lambda argv: subprocess.CompletedProcess(argv, 1, "", "外部操作はありません"), error=exc)
        if not ok:
            raise InstallerError(f"復元が未完了です。transactionを確認してください: {tx.root}") from exc
        raise
