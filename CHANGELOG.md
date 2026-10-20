# Changelog

## 0.1.0-beta.11 ソース版 - 2026-10-20 改造する人向けの見直し

利用者が自分でコードを読んで改造・拡張できるようにする見直し。動作の変更は「ガード」の1件と版番号の表示だけで、ほかの `--help`、hook出力、終了コード、smokeの結果はbeta.10とバイト単位で同一。タグ付きreleaseは未発行。

### 文書と参照

- コード・テスト・スキーマ・公開文書の中の旧非公開文書の決定IDや節番号への参照を、公開ツリー内の見出しへのリンクか、その場の理由に書き直した。参照切れはテスト（`tests/test_doc_refs.py`）で検出する。
- `ARCHITECTURE.md` と `INTERFACES.md` の「上記と異なる場合はこちらを優先」形式の節をなくし、本文を今の動作だけにした。`INTERFACES.md` の版の表記を現在の版に直した。
- 文書とコードの食い違いを文書側で直した: 環境情報の上限（240 token）、runtime CLIの終了コード（2は内部エラー、rollbackなし）、hookは6種、runtimeファイル上限60、profile件数とワーカー数はコードで制限しないこと、`event.schema.json` の説明文（`persona` 部品と新しい4種のイベント）、外部ツール後の文脈注入はCodexだけ、SessionEndの記憶候補抽出はClaude Codeだけ。

### 改造ガイド

- `docs/EXTENDING.md` を追加。よくある改造6種（危険コマンド規則、CLIコマンド、hookの処理、常駐文脈の予算、persona項目、状態スキーマ）ごとに、触るファイル・回すテスト・壊してはいけないことを書いた。
- 今のコードから書き起こした契約（正規化イベント、hookのホスト別出力、イベント種別、常駐文脈の部品と予算、検索の係数、週次レポートのキー、ガード規則、記憶候補、personaの上限）を同じ文書に載せ、コードとのズレをテスト（`tests/test_extending_contracts.py`）で検出する。
- hookが外部プロセスもネットワークも呼ばないことをテスト（`tests/test_hook_isolation.py`）で検査する。

### 名前と構造

- 状態フォルダの場所の決め方について、installerとruntimeの一致をテスト（`tests/test_state_home.py`）で保証した。旧名 `pa_home`・`PA_HOME` は互換と移行の検出だけに残した。
- `core/ctx/cli.py` を入口・引数の組み立て・hookのfail-openの包みだけにし、コマンドの処理を `cmd_task.py`・`cmd_memory.py`・`cmd_persona.py`・`cmd_admin.py` に、共通の補助を `cli_common.py` に分けた。`python3 core/ctx/cli.py` の起動と既存の固定参照はそのまま動く。
- `core/ctx/store.py` の汎用部分を `fileio.py`（原子書き込み・JSONL・ロック）、`tomlemit.py`、`schemacheck.py` に分けた。
- 移した名前は `core.ctx.cli` と `core.ctx.store` から引き続きimportできる（0.2.0で外す予定。`tests/test_split_compat.py`）。
- `core/ctx` のモジュール上限を12から20に上げた。runtimeファイルの上限60は維持（51ファイル）。
- installerの `install()`・`uninstall()`・`doctor()` と、`installer/cli.py` の `_install_command`・`main` を名前の付いた段に分けた。

### ガード

- bash形式の `rm` の再帰・強制削除は、フラグの書き方（`-rf`・`-r -f`・`-R -f`・`-r --force` など）によらず、対象がルート・ホーム・親ディレクトリかどうかだけで判定するようにした。以前は `rm -rf build` が許可で `rm -r -f build` が拒否だった。PowerShellの再帰・強制削除の規則は `-fo`〜`-force` を強制フラグとし、単独の `-f`（PowerShellでは `-Filter` と区別できず拒否される）と `--force` を対象から外した。

## 0.1.0-beta.10 ソース版 - 2026-09-09 OS互換性の追補

- macOSの`/var`と`/private/var`の違いでstagingの包含確認が失敗する問題を修正。
- Windows CIと共通試験runnerでUTF-8を明示し、Pythonのpatch版によるargparse選択肢の引用符差を試験で扱う。
- beta.9のWindows運用フィードバックと更新・復元経路を含む。タグ付きreleaseは未発行。

## 0.1.0-beta.9 ソース版 - 2026-09-09 Windows運用フィードバック

- Windows向け`update --restart-update`を追加。対象cacheと登録情報をtransactionに保存し、native plugin managerで更新する。更新後は新規セッションが必要。
- `--source`で指定したソースをmaterialize済みruntimeから両ホストへ導入し、別のGitHubタグが混ざるのを防ぐ。
- symlinkを作れないWindowsのcloneでも、Claudeの共有runtimeを導入時に構成する。main先行の保存先権限診断・案件文脈の維持修正を含む。

- PowerShellの固定CLI、導入記録と一致するlauncher、通常読取、引用内の検索式を判定できるよう修正。未読制約があっても制約取得・状態確認・保留を可能にした。
- 必須制約を全openカードから安定した順序で取得し、R1のStopを一度の注意喚起へ変更。R2・R3、秘密情報保護、完了証拠、現在の利用者指示の照合は維持。
- Windowsの方針内CLI表示、検証runnerの入力照合、同時刻snapshotの保持順を修正。Windows用のfixtureとsmokeを整備。
- 導入時にClaudeの共有runtimeをcanonicalから再構成し、管理launcherのhashを記録。未対応のWindows Codex live updateは状態を変更する前に停止する。
- 本体保守の手順と分離環境でのWindows検証スクリプトを追加。本番反映と実アプリの連続対話は別途確認が必要。

## 0.1.0-beta.8 - 2026-09-07

- 通信失敗後のrollback再試行で、インストーラー自身が復元済みのhost設定を同時編集と誤判定する不具合を修正。
- native undoが設定を部分変更して失敗した場合も、記録した設定を復元して再試行できるよう修正。利用者による後続の編集は引き続き保護する。
- 自己復旧後の再試行・部分失敗・利用者編集保護の回帰テストを追加。beta.7のプロジェクト、サブDA、180スキル機能を含む。

## 0.1.0-beta.7 - 2026-09-07

- 目的・範囲、担当DA、選択した10〜20スキル、出典・日付付き初期文脈を持つプロジェクトの作成・表示・復旧を追加。
- 生成時のruntimeと専用stateを案件内へ固定配置し、親の更新・移動から独立してアプリとCLIから再開できる入口を追加。
- 180スキルの保管パックと、常用18スキルの選択・配置、検索・表示・明示exportを追加。
- 共通探索先の原本一致スキルだけを退避し、常用18個・編集済み・無関係なスキルを保持する移行コマンドを追加。
- `concise`・`warm`・`formal`の3サブDAプリセットと、メインと同じvalidatorを使うpersona選択を追加。
- READMEとプロジェクト操作説明を新版へ更新。生成・復旧・案件分離とCodex app-serverの設定・スキル発見の検証を追加。

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
