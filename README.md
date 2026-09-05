# Kiseki DA

**Kiseki DA（Digital Assistant）** は、Claude Code / Codex に承認制の記憶、証拠付きタスク完了、安全hook、プロジェクト別キャラクターを追加する軽量な個人AIハーネスです。Python 3.11+ の標準ライブラリだけで動き、外部telemetryはありません。

> Status: `v0.1.0-beta.2`（macOS local向け公開beta）。2026-09-05の案件分離・指示優先・証拠照合の修正を含みます。

## 対応範囲

- Host: Claude Code `>=2.1.142`、Codex `>=0.151.0`（CLI検証: Claude Code `2.1.259` / Codex `0.153.3`）
- OS: macOS local。Linux localはbeta運用中に検証を継続
- State: `KISEKI_DA_HOME`（既定 `~/.kiseki-da`）
- 対象外: Windows 11 native、WSL2、cloud session、Cursor、無人実行、人格による権限変更
- App: Claude DesktopはCodeタブのlocal session。Codex Appはprojectの`Local`環境のみ（管理Worktreeはbeta対象外）

## インストールして好きなフォルダで使う

macOS、Python 3.11〜3.14と、CodexアプリまたはClaude Code / Codex CLIが必要です。Codexアプリだけを使っていても導入でき、同梱CLIを自動検出します。Gitリポジトリでないフォルダでも使えます。

```bash
git clone --branch v0.1.0-beta.2 --depth 1 https://github.com/blackrabbit74/kiseki-da.git
python3 kiseki-da/install.py install --host codex --scope user
```

導入が正常終了した後、CLIを使うターミナルで次を実行します。

```bash
export PATH="$HOME/.kiseki-da/bin:$PATH"
kiseki-da doctor
```

Claude Codeだけに導入するなら `--host claude-code`、両方なら `--host all` を指定します。初回の利用者情報・キャラクター設定を確認してください。上の `export` は現在のターミナルに適用されます。常用する場合は同じ行を `~/.zshrc` に追加します。

導入後もCodexアプリで使えます。アプリを再起動し、使いたいフォルダを `Local` で開いてください。ターミナルからCodexを起動する必要はありません。`codex` / `claude` コマンドを導入済みなら、使いたいフォルダからCLIを起動することもできます。

Codexを再起動し、`/hooks`でKiseki DAのhookを確認・trustした後、`kiseki-da doctor --confirm-codex-trust`で確認済みとして記録します。インストーラーだけではtrust済みになりません。

指定したフォルダだけで有効にする場合は、最初のinstallを次の形で実行します。既存フォルダの絶対パスを指定してください。

```bash
python3 kiseki-da/install.py install --host codex --scope project --project "/使いたいフォルダの絶対パス"
```

導入済みなら `kiseki-da project add "/別のフォルダの絶対パス" --yes` で追加できます。`project add` は指定フォルダだけで有効になるproject modeへ切り替えるため、全フォルダで使うuser modeのままなら登録操作は不要です。どちらのmodeも、新しい記憶は案件内が既定です。

[詳しい導入・更新・復旧手順](docs/INSTALLATION.md) ／ [プライバシー](PRIVACY.md)

## 主な操作

```text
kiseki-da setup
kiseki-da persona edit|preview|show|reset
kiseki-da project add|list|remove
kiseki-da session list|clear
kiseki-da context required --page 1
kiseki-da policy show verification
kiseki-da doctor --json
kiseki-da update --dry-run
kiseki-da uninstall
```

従来のtask、search、candidate、approve、reject、remember、reportも`kiseki-da`から利用できます。設計は[ARCHITECTURE.md](docs/ARCHITECTURE.md)、リリース判断は[RELEASE-DECISIONS.md](docs/RELEASE-DECISIONS.md)、脆弱性の連絡方法は[SECURITY.md](SECURITY.md)を参照してください。

Codexが通常のPostToolUseで終了コードを渡さない場合、その結果は安全のため完了証拠になりません。`kiseki-da verify run -- <command> [args...]`で検証コマンドを実行すると、終了コード付きの証拠を記録できます。Claude/Codexを同じscopeで並行利用する場合、SessionStartに表示された`--sid`を各CLI commandへ付けます。省略時に複数sessionを検出すると、混線防止のため書込前に拒否します。

作者: Navigator / License: MIT
