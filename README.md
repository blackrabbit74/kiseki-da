# Kiseki DA

**Kiseki DA（Digital Assistant）** は、Claude Code / Codex に承認制の記憶、証拠付きタスク完了、安全hook、プロジェクト別キャラクターを追加する軽量な個人AIハーネスです。Python 3.11+ の標準ライブラリだけで動き、外部telemetryはありません。

> Status: `v0.1.0-beta.1` release candidate。公開前の最終利用者承認までGitHub Releaseは公開しません。

## 対応範囲

- Host: Claude Code `>=2.1.142`、Codex `0.151`系（公開時に実機合格版を固定）
- OS: macOS local。Linux localはbeta運用中に検証を継続
- State: `KISEKI_DA_HOME`（既定 `~/.kiseki-da`）
- 対象外: Windows 11 native、WSL2、cloud session、Cursor、無人実行、人格による権限変更
- App: Claude DesktopはCodeタブのlocal session。Codex Appはprojectの`Local`環境のみ（管理Worktreeはbeta.1対象外）

## インストール

Release ZIPを展開するか、タグをcloneして同じinstallerを実行します。ダウンロードしたscriptをshellへ直接pipeしません。

```bash
git clone --branch v0.1.0-beta.1 https://github.com/blackrabbit74/kiseki-da.git
cd kiseki-da
python3 install.py install
```

導入前に[インストール手順](docs/INSTALLATION.md)と[プライバシー](PRIVACY.md)を確認してください。Codexは導入後に`/hooks`でhookをtrustし、`kiseki-da doctor --confirm-codex-trust`で現在hashを確認済みとして記録します。

## 主な操作

```text
kiseki-da setup
kiseki-da persona edit|preview|show|reset
kiseki-da project add|list|remove
kiseki-da session list|clear
kiseki-da doctor --json
kiseki-da update --dry-run
kiseki-da uninstall
```

従来のtask、search、candidate、approve、reject、remember、reportも`kiseki-da`から利用できます。設計は[ARCHITECTURE.md](docs/ARCHITECTURE.md)、リリース判断は[RELEASE-DECISIONS.md](docs/RELEASE-DECISIONS.md)、脆弱性の連絡方法は[SECURITY.md](SECURITY.md)を参照してください。

Codexが通常のPostToolUseで終了コードを渡さない場合、その結果は安全のため完了証拠になりません。`kiseki-da verify run -- <command> [args...]`で検証コマンドを実行すると、終了コード付きの証拠を記録できます。Claude/Codexを同じscopeで並行利用する場合、SessionStartに表示された`--sid`を各CLI commandへ付けます。省略時に複数sessionを検出すると、混線防止のため書込前に拒否します。

作者: Navigator / License: MIT
