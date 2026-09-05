# Kiseki DA decisions

形式: `- <YYYY-MM-DD> 決定: … — 理由: … — 廃止条件: …`

- 2026-09-04 決定: 公開名を Kiseki DA（Digital Assistant）、識別子を kiseki-da、初回版を 0.1.0-beta.1 とする — 理由: キャラクターを選べる柔らかさと既存の薄いDA境界を保ち、OSを名乗らない — 廃止条件: 公開前の利用者判断で名称を変更したとき
- 2026-09-04 決定: Claude CodeとCodexを一つのGitHub marketplaceからdual-manifest pluginとして配布し、host設定の直接統合を既定経路から外す — 理由: native managerのcache/update/uninstallとplugin-root解決を使い、絶対パスと既存設定破壊を避ける — 廃止条件: いずれかのhostがplugin hookを廃止または必須機能を提供できなくなったとき
- 2026-09-04 決定: キャラクターは8固定項目＋200文字自由記述、persona block最大220 tokensとし、権限・記憶・検証から分離する — 理由: UXに効く設定だけを構造化し、文脈汚染と擬人化による過信を測定可能にする — 廃止条件: E3で品質低下または効果なしと判定したとき
- 2026-09-04 決定: project modeは共通identity/constraints/preferencesを継承し、personaと案件状態をUUID単位で分離する — 理由: キャラクターと履歴のproject間混線を防ぎつつ共通の利用者制約を保つ — 廃止条件: 複数project運用で継承規則が訂正を3回以上生んだとき
- 2026-09-04 決定: 公開installerはtransaction、backup、doctor、rollbackを持ち、自動更新と状態全削除を提供しない — 理由: 明示的な人間判断と復元可能性を優先する — 廃止条件: native managerが同等のcross-host transactionを提供したとき
- 2026-09-04 決定: Windows nativeとWSL2は独立stateとし、Windows 11実機canary完了をbeta公開条件にする — 理由: commandWindows、locking、PATH、hook dispatchをhosted CIだけでは保証できない — 廃止条件: 公式の再現可能なWindows integration test環境が提供されたとき
- 2026-09-04 決定: background researchは公開するが、直接source linkと引用監査が完了するまでreleaseをblockedにする — 理由: 設計根拠を公開しつつ第三者資料の出典と著作権境界を守る — 廃止条件: 全evidence rowの監査と人手承認が完了したとき
- 2026-09-05 決定: 2026-09-04のWindows/WSL公開gateを廃止し、両環境を検証待ちのbeta.1対象外にする — 理由: 未検証のsupport表明を避けつつmacOSでbeta利用を開始する — 廃止条件: 各実環境canaryが完了し、別versionで対応を宣言するとき
- 2026-09-05 決定: Claude/Codex validator、GitHub Actions matrix、persona実モデル比較、Mac実ユーザーcanaryをrelease blockerから外し、beta利用中の観測項目にする — 理由: 利用しながら試す前提でbetaを公開するという利用者判断 — 廃止条件: beta運用でrelease前gateへ戻す必要がある重大事故が発生したとき
- 2026-09-05 決定: 2026-09-04のbackground公開方針を廃止し、`docs/background/`をbeta.1公開物から除外する — 理由: 未監査資料を公開せず、検証済みprivate backupに保持する — 廃止条件: 出典・引用・license監査と別途公開承認が完了したとき
- 2026-09-05 決定: Codex Appのproject scopeはbeta.1では`Local`限定とし、管理Worktreeを対応対象外と明記する — 理由: 管理Worktreeは`$CODEX_HOME/worktrees`にあり、現在のcanonical path registryでは元repositoryへ対応付けられない — 廃止条件: worktree-aware scope resolverが実装・検証されたとき
- 2026-09-05 決定: machine-readable release gateは対象commit/treeに対する最終利用者承認だけを必須にする — 理由: その他の項目は対象外化または非blocking beta観測へ移した — 廃止条件: 利用者が公開方針を変更したとき

- 2026-09-05 決定: 同日のv2.4修正を公開betaへ統合。新規記憶は案件内が既定で、制約も自動で共通へ保存しない。明示的な共通化は全sectionで共通storeへ保存し、projectへ継承する — 理由: 本日のユーザー判断と一致させる — 廃止条件: 継承範囲の新しい明示判断があるとき。
- 2026-09-05 決定: 証拠・指示の出所をevidence.pyにまとめ、12モジュールと60runtimeファイルの上限を保持する。手動adapter生成は配布せず、native pluginと固定CLI入口で同じ動作を提供する — 理由: persona/scopeと最新修正を重複なく配布する — 廃止条件: 独立したadapter対応を採択したとき。
- 2026-09-05 決定: 任意ディレクトリにはuser scopeを案内し、限定利用にはproject scopeを案内する。shell startupは自動編集せず、導入完了時に絶対launcherとPATH設定例を表示する — 理由: 配布元への依存をなくし既存環境を保持する — 廃止条件: ユーザーが別の導入方式を指定したとき。
- 2026-09-05 決定: Codexの文字列stdoutだけでは成功判定しない既存の厳格な規則を保持し、verify runに実行ID・案件・完全入力hashを追加する — 理由: 出力本文を終了状態と誤認しない — 廃止条件: ホストが構造化された成功状態を保証するとき。

- 2026-09-05 決定: beta.2では、Codexアプリのみ利用しているMacで同梱CLIを自動検出する。明示指定とPATHを優先し、既知のアプリ配置先の実行可能ファイルだけをfallbackにする — 理由: codex未登録で初回導入が止まった実例を解消する — 廃止条件: ホストがアプリCLIの公式検出APIを提供したとき。
