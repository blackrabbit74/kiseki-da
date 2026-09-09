# 個人利用環境の保守

## 通常利用のガード

読取、必須制約の取得、状態確認、カードの保留は、未読制約があっても実行できる。変更・分類不能なスクリプトは制約を全ページ取得してから進める。カードの表示は2件まででも、必須制約は全openカードから取得する。

PowerShellではSessionStartに表示される `& 'Pythonの絶対パス' 'cli.pyの絶対パス' --home '状態領域'` を使用する。Pythonの `-B`・`-I`・`-u` 等にも対応する。PATH上の `kiseki-da` は、更新処理が記録したlauncherとbootstrapのhash、および選択runtimeが一致するときだけ管理操作として識別する。旧導入環境でこの記録がない場合は表示された固定CLIを使い、新インストーラーで更新する。

引数の引用内の `release|deploy` は検索文字列として扱う。引用外のパイプ・リダイレクト・連結、変数展開や分類不能な構文を読取扱いにはしない。`verify run`・導入・更新・案件生成は管理操作の免除対象ではない。hook入口はホスト専用である。

R1のopenカードは一度注意喚起し、記録を残して応答を終了できる。自動でclose・deferしたり、未検証を消したりしない。R2・R3は従来の一度限りのStopゲートを維持する。closeには引き続き条件と一致する成功証拠が必要である。

## ガード本体を直すとき

1. 利用者が、対象ソース、目的、許可する変更範囲を定めた保守用セッションを用意する。通常セッションに注入された制限をエージェント自身で解除する機構や環境変数は設けない。
2. 適用中の上位指示・権限を確認する。編集禁止がある場合は適用元を示す。通常のhook trust、sandbox、ホストのapprovalは変更しない。
3. ソースの未コミット差分を保存し、ガード・方針・導入処理を変更する。インストール済みcacheを直接編集しない。
4. Python単体試験、両ホストの起動、PowerShell管理操作、制約取得→作業→証拠→close/deferを確認する。fixtureによるhook試験と実アプリでの対話確認は区別して記録する。
5. 適用前に対象・差分・バックアップ・rollbackを提示し、ホストが要求する権限確認を通す。公開・push・リリースは別の明示指示があるときだけ行う。

## ローカルソースからの更新

```powershell
& 'Pythonの絶対パス' .\install.py update --source 'ソースの絶対パス' --restart-update --dry-run
& 'Pythonの絶対パス' .\install.py update --source 'ソースの絶対パス' --restart-update
```

更新は既存のtransaction・native plugin managerを使用する。Windowsで実体化されたClaude用ディレクトリが古くても、配布runtimeの作成時にcanonicalの `plugins/kiseki-da` から再構成する。人格・記憶・証拠・未検証記録は保持する。実行中の旧セッションに新しい方針が自動反映されたとは扱わない。

`--restart-update`は異なるversionの導入に使用する。対象pluginのcache familyと登録情報を既存transactionへバックアップし、各ホストの正規plugin managerに更新を任せる。旧runtimeは復元用に保持する。更新後の新規セッションを前提とし、旧セッションの継続動作は保証しない。失敗時は旧runtimeを供給元としてpluginを戻し、保存したhost設定・cacheを復元する。利用者の後続編集はhashで検出し、勝手に上書きしない。

保守のため無効化したpluginは、`--restart-update --enable-plugin`を明示した場合だけ再有効化する。ホストのsandbox・approval・hook trustは変更しない。rollbackでは更新前の有効・無効状態も復元する。

従来のCodex live updateはatomicなcache交換に依存し、Windowsでは対応していない。`--restart-update`を付けない実更新は状態を変更する前に停止する。同一versionの異なるcache内容の上書きも拒否する。cacheのファイルを個別編集したり、trustを解除したりする保守手順にはしない。

更新のtransaction IDとjournalのバックアップ先を保存する。戻す場合は `install.py rollback --transaction <ID>` を使用する。更新後に状態が変化した場合、自動rollbackが同時編集を上書きしないことを確認する。バックアップには個人情報を含み得るため、リポジトリや公開ログに含めない。

## Windowsでの再検証

`scripts/check_guard_maintenance.py --output <新しい診断フォルダ> --native` は、分離した状態と実PowerShellで制約取得→変更→証拠記録→close/deferを実行する。任意の `--profile <profile.toml>` で実際の人格をコピーして読込を確認できる。hook payloadは試験側が送信し、実コマンドの終了コードと出力を記録する。実アプリとの連続対話を再現したとは扱わない。`--native` は、分離したCodex plugin managerとClaudeの `--init-only` を検査し、モデルを呼ばない。

`acceptance/smoke.sh` はGit Bashにも対応する。POSIXの300ms予算は維持し、Windowsでは起動時間を観測値として表示する。Windowsの機能試験が成功しても、300ms以内の性能を満たしたという意味ではない。

`scripts/check_windows_update.py --old-source <旧ソース> --new-source <新ソース> --output <新しい診断フォルダ>` は、分離した両ホストの実plugin managerで導入→更新→rollbackと、両ホスト更新後の意図的な失敗からの自動復元を検証する。本番状態やhook trustは変更しない。
