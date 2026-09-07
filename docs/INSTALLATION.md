# インストールと復旧

## 前提

- Python 3.11〜3.14
- CodexのMacアプリ、またはClaude Code / Codexのlocal CLI
- GitHubへ接続できること（clone、install、update時）

`v0.1.0-beta.7`の対応対象はmacOS localです。Linux localはbeta利用中に検証を続けます。Windows 11 nativeとWSL2は検証待ちのため対応対象外です。将来検証用コードが含まれていても、動作保証を意味しません。

## Codexアプリだけを使っている場合

ターミナルでCodexを起動した経験は不要です。v0.1.0-beta.2から、インストーラーは次の順にCLIを探します。doctor・update・uninstallでも同じ探索を使います。

1. `KISEKI_DA_CODEX_COMMAND` で利用者が明示指定したコマンド
2. ターミナルのPATH上の `codex`
3. macOSの `/Applications`、続いて `~/Applications` にある `ChatGPT.app` / `Codex.app` の `Contents/Resources/codex`

見つかった実行ファイルはPython・CLIのversion・plugin managerの機能を通常どおり検査します。PATHやshell startupを自動変更しません。アプリを別の場所へ置いている場合は `KISEKI_DA_CODEX_COMMAND` に引用符付きの絶対パスを指定してください。

```bash
KISEKI_DA_CODEX_COMMAND='"/アプリの保存先/ChatGPT.app/Contents/Resources/codex"' \
  python3 install.py install --host codex --scope user
```

`codex のCLIが見つかりません` と表示されたbeta.1からやり直す場合、同じcloneの中で次を実行します。公開タグを指定したcloneの `detached HEAD` 表示は、このインストール用途では問題ありません。手元に編集がある場合は退避してから切り替えてください。

```bash
git fetch origin tag v0.1.0-beta.7
git switch --detach v0.1.0-beta.7
python3 install.py install --host codex --scope user
```

インストールの失敗後に `kiseki-da` が見つからないのは、まだlauncherが作られていないためです。先に上のinstallを完了してください。導入後の利用はCodexアプリの `Local` 環境で行えます。

## 導入

GitHub ReleasesからZIPと`SHA256SUMS`を別々に保存し、SHA-256を照合してから展開します。macOS/Linuxは`shasum -a 256 kiseki-da-0.1.0-beta.7.zip`の結果を`SHA256SUMS`と比較します。downloadしたscriptをshellへpipeして実行しません。cloneする場合は公開済みtagを指定します。

```bash
git clone --branch v0.1.0-beta.7 --depth 1 https://github.com/blackrabbit74/kiseki-da.git
cd kiseki-da
python3 install.py install --dry-run
python3 install.py install
```

ZIPを展開した場合も、展開先の同じ`install.py`を実行します。

```bash
python3 install.py install --host all --scope project --project /absolute/project
python3 install.py install --dry-run
```

対話なしで使う場合は、[`answers.example.json`](../answers.example.json)をcopyして全項目を確認し、`python3 install.py install --answers <file> --yes`を実行します。CLI引数を指定した場合はanswersの同じ項目より優先されます。

installerはKiseki DA内の安定launcherに加え、Pythonのuser scripts directoryへ`kiseki-da`（Windowsは`kiseki-da.cmd`）を配置します。shell startupやWindows PATHは自動編集しません。`kiseki-da doctor`がPATH未登録を通知した場合は、表示されたdirectoryを自分のPATHへ追加するか、表示されたlauncherの絶対pathを使います。

installerは事前検査、変更予定表示、backup、staging、plugin manager実行、installed cacheの6 hook smokeの順で処理します。途中で失敗すると自動rollbackします。status 3の場合は表示されたjournalを保全し、同時変更したファイルを確認してから`kiseki-da rollback --transaction <id>`を再実行します。自動復元は利用者変更を上書きしません。

旧`PA_HOME`または`~/.pa`を検出しても自動では使いません。内容を確認後、`--import-legacy`を明示した場合だけ、旧状態を残したまま新しい`KISEKI_DA_HOME`へcopyします。新旧両方に状態がある場合は自動mergeせず停止します。

## 任意ディレクトリから呼ぶ

`--scope user` は任意のフォルダで有効です。`--scope project --project "/absolute/project"` は登録した既存フォルダとその配下だけで有効です。どちらも配布元の場所とは独立し、日本語・空白を含むパスに対応します。プロジェクトへのファイルのコピーやGit初期化は不要です。

既定の状態領域なら、次で現在のターミナルからCLIを使えます。

```bash
export PATH="$HOME/.kiseki-da/bin:$PATH"
kiseki-da version
```

永続化する場合は上のexport行を自分の `~/.zshrc` に追加します。PATHを変更しない場合は `"$HOME/.kiseki-da/bin/kiseki-da" doctor` のように絶対パスで呼べます。`KISEKI_DA_HOME`を変更した場合は、その場所の `bin` を使います。導入完了時にも実際のlauncherとPATH設定例を表示します。

1チャット1案件を基本とし、案件のフォルダから新しいセッションを始めてください。新規カードと記憶の所属は、そのセッションを始めたフォルダに固定します。共通の記憶への昇格には「全案件で『本文』を覚えて」など、ユーザー本人の直接の指示と `--global` が必要です。

## Project scope

plugin登録はhost側のユーザー領域に存在しますが、対象外projectではhookが状態を読む前に空で終了します。project rootはcanonical pathで登録され、状態はランダムUUIDのprivate directoryへ分離されます。

Codex Appでは登録projectを`Local`環境で開いてください。Codex管理Worktreeは`$CODEX_HOME/worktrees`に作られて登録root配下にならないため、beta.1のproject scopeでは自動activateしません。Claude DesktopはCodeタブのlocal sessionを対象とします。Cloud/remote sessionは対象外です。

## Codex trust

Codexを再起動して`/hooks`を開き、Kiseki DAのhookを確認してtrustします。その後、表示された現在の定義を確認した旨を`kiseki-da doctor --confirm-codex-trust`で明示記録します。attestationにはversionとhook SHA-256が入り、更新でhashが変わると再び`pending activation`になります。

## 更新と削除

自動更新はありません。`kiseki-da update --dry-run`で変更を確認し、`kiseki-da update`で明示更新します。`kiseki-da uninstall`はKiseki DAが所有するplugin登録とruntimeだけを外し、個人状態は保持します。

beta.5以降の更新は、実行中のセッションが参照する旧hook cacheを削除しません。Codexのnative `plugin add`は旧cacheを整理するため、一時環境で新版cacheを作り、実環境へ追加配置してから参照tagを更新します。Claudeは旧cacheを保持するmarketplace再登録とplugin installを使用します。更新やrollbackの途中で新しく開始したセッションも保護するため、追加配置したcacheはrollbackでも残します。同じversionの内容が異なる場合は上書きせず停止します。

既存セッションは旧版のまま継続できます。新版の挙動を使うときは新規セッションへ切り替えてください。Claudeによる古いcacheの期限付き整理や、利用者がnative CLIから直接行う削除はhostの管理範囲です。

開発用の実host検証は`python3 acceptance/live_update_smoke.py`で行えます。Claude/Codex CLIが必要です。設定と状態を一時ディレクトリへ分離し、モデルを呼ばずに更新・rollbackと旧hookファイルの継続性を検査します。`--remote`を付けるとGitHubの公開済みタグで参照変更も検証します。

Claude/Codexが異常終了して複数session markerが残った場合、Kiseki DAは混線防止のためSID省略commandを拒否します。`kiseki-da session list`で確認し、終了済みと判断できるmarkerだけを`kiseki-da session clear <session-id> --yes`で明示解除します。

Codexの休止版は`KISEKI_DA_HOME/retained-plugin-caches/codex/`へ保持し、元のcache pathをその保持先へのリンクにします。使用版だけを通常のディレクトリとして残すことで、rollback後に新しいcacheが誤選択されることを防ぎます。切替にはmacOS/Linuxのatomic exchangeが必要で、非対応のファイルシステムではcacheを変更する前に停止します。
