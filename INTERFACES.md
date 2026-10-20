# Kiseki DA Interfaces v2

この文書は公開betaのruntime・installer契約の正本である。旧pa-harness契約と背景調査は検証済みprivate handoff backupに保存し、beta.1の公開treeには含めない。

## 名称とversion

- Display: `Kiseki DA`（Digital Assistant）
- Slug / CLI / plugin / marketplace: `kiseki-da`
- Package version: `0.1.0-beta.1`
- Profile schema: `2`（schema 1はread-compatible）
- State env: `KISEKI_DA_HOME`; default `~/.kiseki-da`。GUI hook用location pointerは既定`~/.kiseki-da-location`

## CLI

公開コマンドはREADME記載の`install/setup/persona/project/session/doctor/update/rollback/uninstall/version`と、`task/search/candidate/approve/reject/remember/report/verify/context/policy`である。`hook`はhost内部用である。旧`adapter render/link`による手動adapter生成とCursor runtimeは配布せず、元workspaceの検証済みbackupだけに残す。

タスクカードは`task set --workspace/--constraint/--next`で案件・制約・次の一手を持つ。`task override --command/--tool/--input/--quote`は、記録済みの利用者発言（user-input hook）と照合できた明示指示を今回の操作だけに結び付け、リスク・未検証状態・ホスト権限は変更しない。省略された文脈は`context required/profile/instruction --page`で全ページを取得し、検証方針は`policy show`で読む。

完了証拠は実行ID・案件・実行日時・完全入力hash・成功状態で照合する。Read対象の変更や後続変更で証拠は失効し、`last`は他sessionの証拠へ戻らない。Codexの文字列出力は終了コードの証拠にしない。`verify run -- <command>`はshellを介さず実行し、終了コード付きの証拠を記録する。

一覧系は`--json`でJSONを返す。変更系は確認前に差分を表示し、厳密な`--dry-run`ではhost CLIも起動せずファイル・plugin manager・networkを変更しない。そのためhost version/inventory probeは実行時planまで延期する。非対話実行は完全なanswers fileと`--yes`を要求する。

installerの終了コードは0=検証済み成功、1=書込前失敗、2=rollback済み失敗、3=rollback不完全、130=中断である。runtime CLI（`task`・`search`など）は0=成功、1=利用者の入力エラー、2=想定外の内部エラー（rollbackは伴わない）、130=中断である。hookだけは常に0でfail-openする。

## Answers JSON

```json
{
  "schema": 1,
  "hosts": ["claude-code", "codex"],
  "activation": {"mode": "project", "projects": [{"path": "/absolute/project", "persona": {}}]},
  "identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]},
  "persona": {},
  "security": {"apply_recommended_host_settings": false},
  "preview": {"enabled": true, "hosts": "selected", "max_rounds": 3}
}
```

未知キーと不完全な非対話回答は書込前に拒否する。project pathは書込前にcanonical absolute pathへ正規化する。answers fileそのものはstateへ複製しない。

## Persona

`name<=32`, `first_person<=16`, `user_address<=32`, `custom_style<=200` Unicode文字。enumはARCHITECTUREとschemaに定義した値だけを許可する。自由記述は一行へ正規化し、秘密やcontrol plane変更要求を拒否する。persona blockは220推定token以下である。

## Scope

activation registryはKISEKI_DA_HOMEごとにuserまたはproject modeのどちらか一方を持ち、選択したClaude/Codexで共有する。project modeは複数rootを持てる。hookはscope判定を全state accessより先に行う。project間のstateとpersonaはUUID単位で分離し、共通identityと明示的に共通化した記憶だけを継承する。user modeでもカードと新しい記憶はworkspaceで選別する。新しい記憶は制約も含めて案件内への保存が既定で、`--global`を付けたときだけ、hostで観測した直接指示と本文を照合して共通storeへ保存する。scope未設定の既存項目は共通として保持する。WindowsとWSLのregistry/state共有は禁止する。同一scopeで複数sessionが有効なら、SID省略CLIを拒否する。

`v0.1.0-beta.1`のCodex App project scopeは`Local`環境限定である。Codex管理Worktree、Windows native、WSL2、Cloudは対応対象外とする。

## Plugin

Claude manifestは`hooks/claude-code.json`と`userConfig.python_executable`を使う。Codex manifestはCodex validatorに従い`hooks`を宣言せず、既定`hooks/hooks.json`を使う。Codex hookはtrustされるまでinactiveである。

hookは6種の正規化イベント（session-start / user-input / pre-tool / post-tool / stop / session-end）を持つ。user-inputは両ホストの`UserPromptSubmit.prompt`から実際の発言を記録するだけで、追加文脈を注入しない。Codexの入力形式は[公式資料](https://learn.chatgpt.com/docs/hooks#userpromptsubmit)に準拠する。常駐文脈は基本方針を含めて2,500推定tokens・9,000文字以内で、カードは丸ごと捨てず要点と固定CLI参照先を残す。必須制約を省略した場合は全ページの取得後に変更を通す。

## Transaction ownership

installerはinstall/update/uninstallだけでなくsetup・persona・project・session marker変更にもtransaction ID、開始時hash、backup、適用結果、rollback結果を残す。native manager操作は実installed cacheを6 hook smokeで検証する。同時変更を検出したファイルは全体復元せず、status 3とjournal path・復旧再試行commandを残す。通常uninstallはstateを削除しない。

## Compatibility

runtimeと両manifestのversionは一致させる。profile readはschema 1/2に対応し、personaの明示確定時だけschema 2へ移行する。schema 1の既存配列と未知TOML key/valueはround-tripで保持する。記憶候補の承認保存はintent journalと元候補IDで再試行できる。`report`は実測していない品質指標をnullで返す。並行writerの強い整合性と実LLMでの品質比較は保証しない。

変更の経緯は[CHANGELOG](CHANGELOG.md)と[DECISIONS](docs/DECISIONS.md)にある。
