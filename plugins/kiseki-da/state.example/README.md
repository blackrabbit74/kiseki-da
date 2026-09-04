# state.example — 状態ディレクトリ（`$KISEKI_DA_HOME`、既定 `~/.kiseki-da/`）の雛形

`kiseki-da init` がこのディレクトリの `profile.toml` を `$KISEKI_DA_HOME/profile.toml` に複製し、
`events.jsonl` / `candidates.jsonl` / `tasks/` / `archive/` / `snapshots/` / `session/` を作る。

- `profile.toml` は利用者の明示発言（`kiseki-da remember`）か承認済み候補（`kiseki-da approve`）でだけ増える。
  手で編集してもよいが、書込は `core/ctx/store.py` を経由し、書込前に `snapshots/` へ複製される。
- `$KISEKI_DA_HOME` は私的領域（mode 700）。コードリポジトリの外に置き、git には入れない。
  絶対パスを外部向けの出力に書かない。
- hook からの `$KISEKI_DA_HOME` 配下へのツール書込は pre-tool ガードが拒否する。書けるのは Kiseki DA プロセスだけ。
- 実データ入りの見本は `core/tests/fixtures/profile.sample.toml` にある。
