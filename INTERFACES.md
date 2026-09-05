# Kiseki DA Interfaces v2

この文書は公開betaのruntime・installer契約の正本である。旧pa-harness契約と背景調査は検証済みprivate handoff backupに保存し、beta.1の公開treeには含めない。

## 名称とversion

- Display: `Kiseki DA`（Digital Assistant）
- Slug / CLI / plugin / marketplace: `kiseki-da`
- Package version: `0.1.0-beta.1`
- Profile schema: `2`（schema 1はread-compatible）
- State env: `KISEKI_DA_HOME`; default `~/.kiseki-da`。GUI hook用location pointerは既定`~/.kiseki-da-location`

## CLI

公開コマンドはREADME記載の`install/setup/persona/project/session/doctor/update/rollback/uninstall/version`と既存の`task/search/candidate/approve/reject/remember/report/verify`である。`hook`はhost内部用、旧`adapter render/link`はlegacy扱いとする。Cursor runtimeは元workspaceの検証済みbackupだけに残し、beta pluginには含めない。

一覧系は`--json`でJSONを返す。変更系は確認前に差分を表示し、厳密な`--dry-run`ではhost CLIも起動せずファイル・plugin manager・networkを変更しない。そのためhost version/inventory probeは実行時planまで延期する。非対話実行は完全なanswers fileと`--yes`を要求する。

終了コードは0=検証済み成功、1=書込前失敗、2=rollback済み失敗、3=rollback不完全、130=中断である。hookだけは常に0でfail-openする。

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

activation registryはKISEKI_DA_HOMEごとにuserまたはproject modeのどちらか一方を持ち、選択したClaude/Codexで共有する。project modeは複数rootを持てる。hookはscope判定を全state accessより先に行う。project間のstateとpersonaは分離する。WindowsとWSLのregistry/state共有は禁止する。同一scopeで複数sessionが有効なら、SID省略CLIを拒否する。

`v0.1.0-beta.1`のCodex App project scopeは`Local`環境限定である。Codex管理Worktree、Windows native、WSL2、Cloudは対応対象外とする。

## Plugin

Claude manifestは`hooks/claude-code.json`と`userConfig.python_executable`を使う。Codex manifestはCodex validatorに従い`hooks`を宣言せず、既定`hooks/hooks.json`を使う。Codex hookはtrustされるまでinactiveである。

## Transaction ownership

installerはinstall/update/uninstallだけでなくsetup・persona・project・session marker変更にもtransaction ID、開始時hash、backup、適用結果、rollback結果を残す。native manager操作は実installed cacheを6 hook smokeで検証する。同時変更を検出したファイルは全体復元せず、status 3とjournal path・復旧再試行commandを残す。通常uninstallはstateを削除しない。

## Compatibility

runtimeと両manifestのversionは一致させる。profile readはschema 1/2に対応し、personaの明示確定時だけschema 2へ移行する。schema 1の既存配列と未知TOML key/valueはround-tripで保持する。

## 2026-09-05 統合契約（上記の旧挙動と異なる場合はこちらを優先）

- `user-input`を第6の正規化hookとして追加。両ホストの`UserPromptSubmit.prompt`から実際の発言を記録し、追加文脈を注入しない。Codexの入力形式は[公式資料](https://learn.chatgpt.com/docs/hooks#userpromptsubmit)に準拠する。
- user modeでもカードと新しい記憶はworkspaceで選別する。project modeはpersona・状態をUUIDで分離し、共通identityと明示的な共通記憶を継承する。制約も案件内保存が既定。`--global`はhostで観測した直接指示と本文を照合し、共通storeへ保存する。既存のscope未設定項目は共通として保持する。
- `task set --workspace/--constraint/--next`、`task override --command/--tool/--input/--quote`、`context required/profile/instruction --page`、`policy show`を追加する。明示指示は今回の操作に結び付け、リスク・未検証状態・ホスト権限を変更しない。
- 完了証拠は実行ID・案件・実行日時・完全入力hash・成功状態で照合する。Read対象の変更や後続変更で証拠を失効させ、`last`で他sessionへ戻らない。Codexの文字列出力は終了コードの証拠にせず、`verify run`で構造化した証拠を記録できる。
- 常駐は基本方針を含め2,500推定tokens・9,000文字以内。カードを丸ごと捨てず要点と固定CLI参照先を保持する。必須制約を省略した場合は全ページの取得後に変更を通す。personaは220推定tokens以内。
- 承認保存はintent journalと元候補IDで再試行できる。実測していない品質指標はnull。並行writerの強い整合性、実LLMの品質比較、Windows/WSL/Cloud/管理Worktree対応は未実施または対象外。
