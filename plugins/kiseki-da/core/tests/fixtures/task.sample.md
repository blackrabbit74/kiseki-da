id: 2026-09-03-auth-refresh
status: open
risk: R1
kind: code
created: 2026-09-03T10:01:00+09:00
updated: 2026-09-03T11:20:00+09:00
budget: context_tokens=30000 worker_max=0 iterations_max=3 search_max=3

# Goal
認証トークンの自動更新を追加する。理由: 60 分でセッション切れが起きている（利用者の言葉）。

# Done criteria
| id | claim | check | evidence | status |
|---|---|---|---|---|
| C1 | 更新処理の単体テストが通る | pytest tests/test_auth.py -q | ev:s-fx-1:6 | pass |
| C2 | 既存テストに回帰がない | pytest -q | - | open |
| C3 | 変更差分を読み返した | Read /repo/git-diff.txt | ev:s-fx-1:8 | pass |

# Constraints / Out of scope
- 本番 DB 直接書込禁止（c1）。UI 変更は対象外。

# Assumptions
- 更新間隔は 15 分（利用者回答 ev:s-fx-1:5）。

# Open questions
- リフレッシュ失敗時の再試行回数

# Decisions
- 2026-09-03 リフレッシュはバックグラウンドスレッドではなく要求時に行う（理由: 既存構成に常駐プロセスがない）。

# Log
- 2026-09-03T11:20:00+09:00 note: テストを追加した
