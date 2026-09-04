# タスクカード（Kiseki DA）

## いつ書くか
- 非自明なタスクに書く: 複数ステップ、ファイルや外部への副作用、中断後に再開する可能性、のどれかがあるもの。
- 自明なタスク（一手で終わる読取や回答）には書かない。
- 作成は `kiseki-da task new --goal "<目標>" --risk R1 --kind code`。R1 以上のカードが open のままだと stop ゲートが一度だけ止める。

## 雛形（`kiseki-da task show` が出す正規形。見出しは 7 つ、順序固定、空でも残す）

```
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
| C1 | 更新処理の単体テストが通る | pytest tests/test_auth.py | ev:s-fx-1:6 | pass |
| C2 | 変更差分を読み返した | Read git diff | - | open |

# Constraints / Out of scope
- 本番 DB 直接書込禁止（c1）。UI 変更は対象外。

# Assumptions
- 更新間隔は 15 分（利用者回答 ev:s-fx-1:5）。

# Open questions
- リフレッシュ失敗時の再試行回数

# Decisions
- 2026-09-03 リフレッシュは要求時に行う（理由: 既存構成に常駐プロセスがない）。

# Log
- 2026-09-03T11:20:00+09:00 note: テストを追加した
```

ヘッダは `id` / `status`（open | done | deferred | abandoned）/ `risk`（R0..R3）/ `kind`（code | research | decision | ops | writing）/ `created` / `updated` / `budget`（`k=v` 空白区切り）。ヘッダにコメントは書かない。

## 完備規則
- Goal は利用者の言葉で書き、理由（なぜやるか）を添える。
- 完了条件は claim（何が真になるか）＋ check（それを確かめるツールかコマンド）。check は証拠を生むツール名かコマンド名で書き始める（`pytest tests/x.py`、`Read git diff`、`Grep <pattern>`、`curl -i <url>`）。散文の check（「動作を確認する」）は照合できない。
- 各 claim は反証条件（何が起きたら偽か）が言える粒度にする。言えない条件は分割する。
- evidence は `ev:<sid>:<seq>`。`kiseki-da task set <id> --evidence C1=last` で直近の tool_call を結び付ける（`last:<tool>`、`ev:<sid>:<seq>` も可）。手で書かない。
- 条件の id は C1.. の連番。消しても再採番しない。
- カード全体は ≤800 tokens。超えるなら Out of scope に切り出す。
- budget 行は助言。コードは強制しない（段階ごとの目安は verification.md の表）。
- status の遷移: open→done は `kiseki-da task close <id>` だけ（全条件の証拠が照合できたときのみ。欠落があれば何も書き換えず、欠落を `<Cn>: <理由>` で列挙する）。open→deferred は `kiseki-da task defer <id> --reason "<未検証の内容>"`（未達条件は unverified になり、理由が # Log に残る）。abandoned は `--status abandoned`。
- 未確定点は `--question`、置いた仮定は `--assume`（どちらもイベントとして記録される）。決定は `--decide`（日付と理由）。経過は `--note`。

## kiseki-da task コマンド
- `kiseki-da task new --goal "<目標>" [--risk R1] [--kind code] [--id <slug>]`
- `kiseki-da task show <id>` / `kiseki-da task list [--status open|done|deferred|abandoned|all]`
- `kiseki-da task set <id> --add-criterion "<claim> :: <check>"`
- `kiseki-da task set <id> --evidence C1=last` （`last:<tool>` / `ev:<sid>:<seq>` も可）
- `kiseki-da task set <id> --assume "<仮定>" | --question "<未確定点>" | --decide "<決定と理由>" | --note "<経過>" | --risk R2 | --status abandoned`
- `kiseki-da task close <id>` / `kiseki-da task defer <id> --reason "<理由>"`
- `kiseki-da task brief <id> --role research|review [--scope <範囲>]`
