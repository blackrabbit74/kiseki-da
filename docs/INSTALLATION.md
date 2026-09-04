# インストールと復旧

## 前提

- Python 3.11〜3.14
- Claude CodeまたはCodexのlocal CLI
- GitHubへ接続できること（clone、install、update時）

`v0.1.0-beta.1`の対応対象はmacOS localです。Linux localはbeta利用中に検証を続けます。Windows 11 nativeとWSL2は検証待ちのため対応対象外です。将来検証用コードが含まれていても、動作保証を意味しません。

## 導入

GitHub ReleasesからZIPと`SHA256SUMS`を別々に保存し、SHA-256を照合してから展開します。macOS/Linuxは`shasum -a 256 kiseki-da-0.1.0-beta.1.zip`の結果を`SHA256SUMS`と比較します。downloadしたscriptをshellへpipeして実行しません。cloneする場合は公開済みtagを指定します。

```bash
git clone --branch v0.1.0-beta.1 --depth 1 https://github.com/blackrabbit74/kiseki-da.git
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

installerは事前検査、変更予定表示、backup、staging、plugin manager実行、installed cacheの5 hook smokeの順で処理します。途中で失敗すると自動rollbackします。status 3の場合は表示されたjournalを保全し、同時変更したファイルを確認してから`kiseki-da rollback --transaction <id>`を再実行します。自動復元は利用者変更を上書きしません。

旧`PA_HOME`または`~/.pa`を検出しても自動では使いません。内容を確認後、`--import-legacy`を明示した場合だけ、旧状態を残したまま新しい`KISEKI_DA_HOME`へcopyします。新旧両方に状態がある場合は自動mergeせず停止します。

## Project scope

plugin登録はhost側のユーザー領域に存在しますが、対象外projectではhookが状態を読む前に空で終了します。project rootはcanonical pathで登録され、状態はランダムUUIDのprivate directoryへ分離されます。

Codex Appでは登録projectを`Local`環境で開いてください。Codex管理Worktreeは`$CODEX_HOME/worktrees`に作られて登録root配下にならないため、beta.1のproject scopeでは自動activateしません。Claude DesktopはCodeタブのlocal sessionを対象とします。Cloud/remote sessionは対象外です。

## Codex trust

Codexを再起動して`/hooks`を開き、Kiseki DAのhookを確認してtrustします。その後、表示された現在の定義を確認した旨を`kiseki-da doctor --confirm-codex-trust`で明示記録します。attestationにはversionとhook SHA-256が入り、更新でhashが変わると再び`pending activation`になります。

## 更新と削除

自動更新はありません。`kiseki-da update --dry-run`で変更を確認し、`kiseki-da update`で明示更新します。`kiseki-da uninstall`はKiseki DAが所有するplugin登録とruntimeだけを外し、個人状態は保持します。

Claude/Codexが異常終了して複数session markerが残った場合、Kiseki DAは混線防止のためSID省略commandを拒否します。`kiseki-da session list`で確認し、終了済みと判断できるmarkerだけを`kiseki-da session clear <session-id> --yes`で明示解除します。
