# Changelog

## 0.1.0-beta.6 - 2026-09-05

- Git marketplaceの参照タグ変更を、Claudeのsource宣言と矛盾しない再登録手順へ修正。旧cacheは保持する。
- Codexの一覧が省略するrefを設定から補完し、rollback時に元のGitタグを正確に復元する。
- Codexの使用版を明示するため、休止版を保持領域へのリンクに切り替える。ディレクトリとリンクはatomic exchangeし、稼働中hookのパスを途切れさせない。
- ローカルsourceと実GitHubタグの両方で、更新・rollback後の使用版と旧hook継続性を検証する。

## 0.1.0-beta.5 - 2026-09-05

- 更新時に稼働中の旧hook cacheを保持するよう修正。Codexは隔離したnative installで作った新版cacheを追加配置し、Claudeはcacheを保持するnative updateを使う。
- rollbackでも公開済みcacheを保持し、元のmarketplace source/refを復元してから旧版へ戻す。
- 実CLIで更新・失敗時rollback中の旧hook継続性を確認する`acceptance/live_update_smoke.py`を追加。

## 0.1.0-beta.4 - 2026-09-05

- Claude native installがplain textを返す環境でも、更新後のinventoryから新しいcache pathを取得するよう修正。旧cacheを検証して更新がrollbackされる問題を解消。

## 0.1.0-beta.3 - 2026-09-05

- ClaudeとCodexのplugin rootを分離し、ClaudeがCodex用hookを二重読込してツール実行をブロックする障害を修正。
- source/cache検証にhost混入検出を追加し、installed smokeで実際のhook command・argsを実行するよう変更。
- 共通runtimeは原本を共有し、release archiveではリンクを実体化して自己完結させる。

## 0.1.0-beta.2 - 2026-09-05

- Macのターミナルにcodexが未登録でも、ChatGPT.app / Codex.appの同梱CLIを自動検出するよう修正。install・doctor・update・uninstallへ適用。
- 明示的なコマンド指定とPATH上のCLIを優先し、アプリ内の実行ファイルにも通常のversion・plugin検査を適用。
- アプリ利用者向けの前提・再インストール手順と、CLIが見つからない場合の案内を追加。

## 0.1.0-beta.1 - 2026-09-05

- pa-harnessをKiseki DA（Digital Assistant）として再構成。
- Claude Code / Codexのdual-manifest plugin packagingを追加。
- transaction、rollback、doctorを備えた公開installerを追加。
- schema 2の小さなキャラクター設定とproject scopeを追加。
- `KISEKI_DA_HOME`と明示的な旧`PA_HOME`移行を追加。
- macOS localをbeta.1対応対象とし、Linuxはbeta観測、Windows 11 / WSL2は検証待ちの対象外として整理。
- 複数host sessionのSID混線防止、実plugin cacheの6 hook smoke、設定変更transactionを追加。
- release gateをversion・commit・tree・最終利用者承認へ結合し、validator・CI・persona品質はbeta観測へ移行。
- 未監査のbackground資料を公開treeから除外し、Codex AppはLocal限定と明記。

- 2026-09-05の最新版を統合: 案件ごとのカード・記憶分離、現在のユーザー指示の優先、制約のページ取得、完全入力hashによる証拠照合、承認処理の再試行。
- UserPromptSubmitの記録hookを両ホストへ追加。記憶の共通化は明示指示がある場合だけ行う。
- 任意のフォルダで利用するuser scopeと、指定フォルダ限定のproject scopeの導入手順を追加。
- 配布元・状態領域の日本語／空白パス、固定CLI入口、複数runtimeを同一プロセスで扱う場合のimport先を修正。
