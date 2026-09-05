# Kiseki DA Architecture

Kiseki DA（Digital Assistant）は、host LLMを置き換えず、承認済み文脈、タスク証拠、危険操作guard、短いキャラクター設定を付加するlocal-first control planeである。runtimeはPython 3.11+標準ライブラリだけで動く。

## 境界

Kiseki DAが所有するのは、状態、文脈選択、タスクカード、証拠参照、hook正規化、キャラクター表現、installer transactionである。モデル推論、ツール実行、host permission、sandbox、compactionはClaude Code / Codexが所有する。

キャラクターはDigital Assistantの表現層であり、権限主体ではない。事実、安全、承認、記憶書込、検証、完了判定は既存の決定論的control planeから変更できない。

## 配布構造

```text
GitHub marketplace
  ├─ plugins/kiseki-da/                 # Codex入口・共通runtime原本
       ├─ .codex-plugin/plugin.json
       ├─ hooks/hooks.json
       ├─ scripts/hook_entry.py
       ├─ LICENSE
       └─ core/ctx/*
  └─ plugins/claude-code/kiseki-da/     # Claude専用入口
       ├─ .claude-plugin/plugin.json
       ├─ hooks/claude-code.json
       └─ core, scripts, evals, state.example, LICENSE → 共通原本

KISEKI_DA_HOME（既定 ~/.kiseki-da）
  ├─ profile.toml
  ├─ events.jsonl / candidates.jsonl / tasks/
  ├─ projects.json
  ├─ projects/<uuid>/{profile.toml,events.jsonl,candidates.jsonl,tasks/}
  ├─ runtime/<version>/
  ├─ transactions/<id>/{journal.json,backups/}
  ├─ security-backups/<host>/
  ├─ install/codex-hook-trust.json
  └─ install.json

~/.kiseki-da-location  # custom KISEKI_DA_HOMEをGUI hookへ伝えるprivate pointer
```

plugin cacheは交換可能で、利用者状態を保存しない。installerは同じreleaseのruntimeをversion付きで配置し、Claude/Codexのnative plugin managerを利用する。

Claudeは既定の`hooks/hooks.json`とmanifest指定のhookを併合するため、両hostを同じplugin rootから配布しない。共通ファイルはmarketplace内の相対symlinkで共有し、Claudeのmarketplace installで実ファイルとしてcacheへ取り込む。release archiveも追跡済みsnapshotからsymlinkを実体化する。開発時はmarketplace経由で導入する（外部リンクを含む`--plugin-dir`は使用しない）。

## セッションデータフロー

1. plugin hookがhost payloadを5種の正規化イベントへ変換する。
2. scope resolverがcwdをactivation registryと照合する。対象外なら読取・書込せず空で終了する。
3. SessionStartが基本方針、キャラクター、共通制約・選好、現在projectのカード要約を最大2,500推定tokenで一度だけ注入する。
4. PreToolUseが危険操作をdeny/askへ分類する。host permissionとsandboxは迂回しない。
5. PostToolUseが結果の成功状態、長さ、hashを証拠eventとして保存する。
6. task closeが完了条件と証拠IDを突合する。Stopは未完了のR1以上カードを一度だけ止める。
7. SessionEndは明示発言だけを記憶候補にし、承認前にprofileへ入れない。

同じscopeでClaude/Codex sessionが並行する場合はactive SIDを個別markerで保持する。CLIへSIDが無ければ書込前に拒否し、別hostのtask/evidenceへ誤帰属させない。異常終了markerは利用者が`session list/clear`で明示復旧する。

## 文脈予算

- 全体: 2,500推定token、9,000文字
- 基本方針: 800 token以下
- キャラクター: 220 token以下、自由記述200文字以下
- 進行中カード: 400 token以下
- 環境情報: 150 token以下
- 予算超過時: goals、自由記述、persona任意項目、preferences、カード詳細、constraintsの順に縮小する。カードの要点と参照先は残し、必須制約の省略を明示して全ページ取得を要求する

何を入れたかはcontext manifestへ記録する。会話全文、他projectの履歴、背景設計書は常駐させない。

## 状態とscope

user modeは一つの共通状態を使う。project modeはglobal identity・共通constraints/preferencesを継承し、persona、project preferences/facts/goals、candidates、tasks、eventsをUUID単位で分離する。検索はglobal profileと現在projectだけを対象にする。

project rootはcanonical pathでregistryに保存するが、project directoryへ個人状態を書かない。Codex Appはbeta.1では`Local`限定で、`$CODEX_HOME/worktrees`配下の管理Worktreeはproject scopeの対象外とする。Windows nativeとWSL2は検証待ちのためbeta.1の対応対象外である。

## Installer transaction

すべての変更操作は preflight → preview → backup → staging → apply → verify → commit の順で行う。host inventoryと設定hashはlock取得後にも再照合し、installed plugin cacheの6 hookを一時stateでsmokeする。失敗は逆順rollbackし、未完了journalがある間は別変更を開始しない。通常uninstallは個人状態を残す。

## 観測と実験

`events.jsonl`が唯一の実行ログで、`report`が週次指標と監査候補を返す。personaの価値とhost差はbeta利用中に観測する。権限境界の変化、重大な事実性低下、現在指示の不遵守が見つかった場合はpersonaを停止または修正する。

旧pa-harness設計、KILL TEST、背景調査は検証済みhandoff backupに保持し、beta.1の公開treeには含めない。

## 2026-09-05 統合契約（上記の旧挙動と異なる場合はこちらを優先）

- `user-input`を第6の正規化hookとして追加。両ホストの`UserPromptSubmit.prompt`から実際の発言を記録し、追加文脈を注入しない。Codexの入力形式は[公式資料](https://learn.chatgpt.com/docs/hooks#userpromptsubmit)に準拠する。
- user modeでもカードと新しい記憶はworkspaceで選別する。project modeはpersona・状態をUUIDで分離し、共通identityと明示的な共通記憶を継承する。制約も案件内保存が既定。`--global`はhostで観測した直接指示と本文を照合し、共通storeへ保存する。既存のscope未設定項目は共通として保持する。
- `task set --workspace/--constraint/--next`、`task override --command/--tool/--input/--quote`、`context required/profile/instruction --page`、`policy show`を追加する。明示指示は今回の操作に結び付け、リスク・未検証状態・ホスト権限を変更しない。
- 完了証拠は実行ID・案件・実行日時・完全入力hash・成功状態で照合する。Read対象の変更や後続変更で証拠を失効させ、`last`で他sessionへ戻らない。Codexの文字列出力は終了コードの証拠にせず、`verify run`で構造化した証拠を記録できる。
- 常駐は基本方針を含め2,500推定tokens・9,000文字以内。カードを丸ごと捨てず要点と固定CLI参照先を保持する。必須制約を省略した場合は全ページの取得後に変更を通す。personaは220推定tokens以内。
- 承認保存はintent journalと元候補IDで再試行できる。実測していない品質指標はnull。並行writerの強い整合性、実LLMの品質比較、Windows/WSL/Cloud/管理Worktree対応は未実施または対象外。
