# Kiseki DA v0.1.0-beta.1 リリース判断台帳

**決定日:** 2026-09-05

**対象:** `v0.1.0-beta.1`

**状態:** 最終公開承認のみ未決定

「gate廃止」は未検証項目を成功扱いにする意味ではない。beta利用中に検証を続ける非blocking項目へ移し、対応を諦める場合は対応範囲から明示的に外す。

## 決定

| ID | 判断 | beta.1での扱い | 再検討条件 |
|---|---|---|---|
| D-01 | Windows 11 native | 検証待ち。対応対象外 | Windows 11実機でinstall/update/rollback/uninstall、5 hooks、trust、空白・日本語path、並列logを通過したとき |
| D-02 | WSL2 Ubuntu | 検証待ち。対応対象外 | WSL2 22.04/24.04でLinux側state・CLIだけを使うcanaryが通過したとき |
| D-03 | Claude/Codex validator | release gate廃止。利用中に継続確認 | host更新またはmanifest変更時に再実行。失敗版は公開・更新しない |
| D-04 | GitHub Actions matrix | release gate廃止。公開後のbeta運用で確認 | CI失敗時は該当OS/Pythonをsupportedから外すか修正版を出す |
| D-05 | Persona実モデル品質比較 | release gate廃止。利用中に観測 | 権限境界変化、重大な事実性低下、現在指示違反が1件でも出たらpersonaを停止・修正する |
| D-06 | 背景調査資料 | 公開物から除外 | 出典・引用・license監査が完了し、別途公開承認されたとき |
| D-07 | Codex App Worktree | beta.1は`Local`限定と明記 | `$CODEX_HOME/worktrees`を元repositoryへ安全に対応付けるscope解決を実装・検証したとき |
| D-08 | Mac実ユーザー環境canary | release gate廃止。実導入をbeta利用開始とする | 初回利用中の問題は通常のbeta不具合として修正する |
| D-09 | 最終公開承認 | 唯一のrelease blocker | 利用者が対象commit・tracked tree・candidate hashを明示承認したとき |

## beta.1の対応範囲

- 対応: macOS local。Linux localはbeta運用中に検証を継続する。
- Claude Desktop: `Code`タブのlocal sessionを対象とする。
- Codex App: 登録したproject rootの`Local`環境を対象とする。Codex管理WorktreeとCloudは対象外。
- Windows 11 native、WSL2、Cursor、cloud sessionは対象外。
- Windows/WSL向けの試験的コードは将来検証用に残るが、動作保証・support表明は行わない。

## 公開直前に必ず行うこと

1. `python3 tools/publication_audit.py`が`ok: true`であることを確認する。
2. tracked filesだけからcandidateを再生成し、ZIP/tar.gzの内容とSHA-256を検証する。
3. `release-gates`を対象commit・tree hashへ結び、`user_publication_approval`だけを明示承認する。
4. HEADを`v0.1.0-beta.1`でtag付けし、公開予定一覧とhashを再提示する。
5. 利用者承認後にだけGitHubへpushし、public Releaseを作成する。

## 非blocking観測項目

validator、CI、persona品質、Mac実導入で問題が見つかった場合は「既にgateを廃止したから無視する」のではなく、beta不具合として記録する。安全・権限・承認・記憶・検証・完了条件に影響する不具合は即時修正または配布停止とする。
