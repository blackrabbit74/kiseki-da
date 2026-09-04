# 検証方針（Kiseki DA）

リスク段階はタスクカードの `risk` に書く。段階は下げない。上げるのは自由。迷ったら上の段階にする。

## リスク段階表

| 段階 | 対象 | 着手前 | 証拠 | 独立検証 | ワーカー | stop ゲート | worker_max | iterations_max | search_max |
|---|---|---|---|---|---|---|---|---|---|
| R0 | 読取・回答・調査 | なし | なし | なし | 並列の読取調査に ≤3（独立トピックが 2 つ以上のとき） | off | 3（条件付き） | 0 | 3 |
| R1 | 可逆なローカル変更 | 非自明ならカード | 各条件にモダリティ証拠 | なし | なし（既定） | on | 0 | 3 | 3 |
| R2 | 外部に見える／共有に影響（push、共有文書、送信草稿） | カード必須。実行前に差分の要点を提示 | 証拠＋read-back | 条件付き推奨: 変更 >200 行、または認証・権限・データ移行に触れるとき、新規文脈のレビュアー 1 つ | 上記レビュアーのみ | on | 1 | 3 | 3 |
| R3 | 不可逆（削除、デプロイ、支払い、公開、秘密情報、本番） | 環境の権限プロンプトで利用者の明示確認（pre-tool ガードが ask を強制） | 実行後に証拠 | 人の確認が独立検証。サブエージェント無し | なし | on | 0 | 0 | 3 |

- 予算 3 列はカードの `budget` 行に書く助言で、コードは強制しない（`kiseki-da task close` は証拠だけを見る）。
- `worker_max`: 同時に起動するワーカー数の上限。`iterations_max`: 外部信号（テスト・probe）を見て修正をやり直す回数の上限。0 は反復しない。`search_max`: 1 タスクあたりの `kiseki-da search` 回数の目安。
- 外部信号が無い種別は反復しない。自己採点と、同一モデルによる自己審査は完了の根拠にならない。
- `kiseki-da task new` が書く既定の budget は R1 の値。他の段階では表の値を目安に読み替える。

## 証拠モダリティ

| 対象 | 証拠 |
|---|---|
| ファイル | Read |
| コード | テスト実行、または Grep |
| コマンド | 確認済みの出力（post-tool hook が記録した tool_call） |
| HTTP | `curl -i` |
| デプロイ | live probe |
| Web/UI | 実ブラウザ |
| 外観 | 画像を実際に見る |
| 設定 | read-back（書いた値を読み返す） |
| 品質・回帰 | evals の pass^k（v1 未提供。テスト実行で代替し、残りは「未検証」と明記） |

検証器が使えないときは「未検証」と明記して `kiseki-da task defer <id> --reason` する。弱い証拠で代替しない。

## 証拠の照合規則（`kiseki-da task close` が機械的に行うこと）

各完了条件の `evidence` を `events.jsonl` と突き合わせる。判定は次の順で、これ以外の推論はしない。

1. `evidence` が `-` → 証拠がありません（no evidence）。
2. `ev:<sid>:<seq>` が events.jsonl に無い → 証拠イベントが見つかりません（evidence not found）。
3. そのイベントの `type` が `tool_call` でない → ツール呼出のイベントではありません（not a tool call）。
4. `check` の先頭語（小文字化）が read / grep / glob / webfetch / websearch のいずれかなら、イベントの `tool` がその語と一致すること。違えば ツールが一致しません（tool mismatch）。
5. それ以外の先頭語なら、イベントの `tool` が `Bash` で、`target`（実行したコマンド）の先頭語が `check` の先頭語と一致すること。違えば コマンドが一致しません（command mismatch）。加えて `ok` が false でないこと。false なら コマンドが失敗しています（command failed）。
6. `target` と `check` の部分一致は見ない。引数の違いも判定しない。

だから `check` は証拠を生むツール名かコマンド名で書き始める（例: `pytest tests/test_auth.py`、`Read git diff`、`curl -i https://…`）。証拠は `kiseki-da task set <id> --evidence C1=last`（直近の tool_call）で付ける。`last:<tool>`、`ev:<sid>:<seq>` も可。

CodexのPostToolUseが終了状態を渡さない形式では、そのeventは`ok = null`で証拠にならない。`kiseki-da verify run -- pytest -q`のようにshellを介さない検証runnerで再実行し、終了コード付きeventを作る。

## ワーカー

- 用途は (a) R0 の独立した読取調査の並列化、(b) R2 の独立検証、の 2 つだけ。R1 と R3 では使わない。
- 指示書は `kiseki-da task brief <id> --role research|review [--scope <範囲>]` で生成し、そのまま渡す（`worker_dispatch` が記録される）。
- ワーカーは読取専用ツール（Read / Grep / Glob / Web）だけを使い、`kiseki-da` を呼ばず、`$KISEKI_DA_HOME` と `core/` に書かず、入れ子で起動しない。返却は ≤1.5K tokens、見出しは 結論／根拠（出典）／未確認 に固定。
- 返却は主エージェントが検証してから使い、`kiseki-da log worker_return --data '{"task": "<id>", "role": "research", "tokens_est": <n>, "text": "<要約>"}'` で記録する。builder と reviewer は別文脈にする。
