# 固定版基盤を持つ作業環境

v0.1.0-beta.7で追加。インストール済みの`kiseki-da`からも、以下の`python3 install.py`と同じサブコマンドを実行できます。既存環境には[更新手順](INSTALLATION.md#更新と削除)で適用し、共通スキル配置の移行は必要に応じて別途実行します。

メインで相談して範囲を決め、その範囲、担当DA、10〜20スキル、選別した初期文脈を持つ子を作成できます。子の基盤は生成時にコピーされ、親の状態やruntimeが移動・更新されても通常作業は子で完結します。世代制限、自動分割、親子の自動同期は実装していません。

各作業場所の担当DAは1人です。サブDAパックは継続して割り当てる表現設定で、一時的な並列ワーカーとは別です。共通コアは同じ原本と機能契約を意味し、配備した全案件を同時に更新する義務はありません。

## 子の作成

ソースのルートで、作成内容をJSONへ保存します。`context`は必要な項目だけを出典と日付付きで指定し、会話履歴や全profileを渡さないでください。

```json
{
  "name": "調査レポート",
  "goal": "選択した資料を比較し、判断資料をまとめる",
  "scope": "指定された公開資料の調査とレポート作成",
  "persona": "concise",
  "skills": [
    "clarifying-outcomes", "researching-with-sources", "reviewing-literature",
    "auditing-source-credibility", "retrieving-context", "extracting-insights",
    "synthesizing-documents", "comparing-options", "structuring-arguments",
    "verifying-deliverable-completion"
  ],
  "context": [
    {"text": "意思決定の根拠を比較表にする", "source": "依頼メモ", "date": "2026-09-07"}
  ],
  "source_task": "元カードのIDまたは参照先"
}
```

```bash
python3 install.py project create /絶対パス/調査レポート --answers child.json --dry-run
python3 install.py project create /絶対パス/調査レポート --answers child.json
python3 install.py project show /絶対パス/調査レポート
```

`--dry-run`は書き込みを行わず、目的、範囲、DA、選択スキル、初期文脈と生成先を表示します。既存フォルダにも生成できますが、生成対象のファイルや選択スキルが既にある場合は上書きせず停止します。他の成果物は保持します。通常の失敗は変更を復元し、同じ作成コマンドを再実行できます。プロセス中断でtransactionが残った場合は次の操作で復旧してから再試行します。

```bash
python3 install.py project recover /絶対パス/調査レポート
```

復旧は生成途中のtransactionだけが対象で、完成済みの子は取り消しません。同時に編集されたファイルは削除せず、復旧できない対象を報告します。journalは`.kiseki/transactions/`に残ります。

## 再開

アプリで生成したフォルダをLocal案件として開くか、そのフォルダで`codex`／`claude`を起動します。ホストが要求するprojectとhookの信頼確認を行ってください。生成処理は信頼記録や権限を変更しません。子の設定は、親の`kiseki-da@kiseki-da`だけをその子内で無効にし、子の固定版入口へ接続します。

Codexのproject-local hookと信頼確認は[公式Hooks文書](https://learn.chatgpt.com/docs/hooks)を参照してください。設定のマージとスキル発見は同梱app-serverでも検証しています。

```bash
python3 .kiseki/entry.py task list --sid 現在のsession-id
python3 .kiseki/entry.py persona show --sid 現在のsession-id
python3 .kiseki/entry.py search 検索語 --sid 現在のsession-id
python3 .kiseki/entry.py skills list 調査語
```

生成物は次の構成です。

| 場所 | 内容 |
|---|---|
| `.kiseki/project.json` | ID、目的・範囲、DA、選択スキルとhash、基盤version/hash、出典 |
| `.kiseki/runtime/` | 生成時点の固定版基盤と保管パック |
| `.kiseki/state/` | 子専用のタスク、記憶、証拠、session |
| `.kiseki/entry.py` | 子の保存先とruntimeを選ぶ入口 |
| `.kiseki/brief.md` | 精選した初期文脈の全文と出典・日付 |
| `.agents/skills/`、`.claude/skills/` | 選択した10〜20個と関連ファイル |
| `.codex/`、`.claude/settings.local.json` | 各ホストのローカル接続 |
| `KISEKI.md` | 起動案内 |

初期文脈は資料としてcaptureへ保存し、長期記憶の承認を作りません。常駐には短い要約と取得先を入れ、方針を含む2500推定tokens／9000文字の枠内で数えます。通常の候補・承認・検索・証拠付き完了は既存runtimeを使います。元カードを自動で複製・完了にはしません。

## メイン18個と保管180個

新しいメイン用フォルダには`project create`で`--role main`を指定し、`skills`を省略すると合意済み18個を選びます。DAは既存形式のpersona JSONでも指定できます。既存メインの状態は自動でコピーしません。

保管パックは、子では`.kiseki/runtime/packs/skills/`、共通インストールでは`KISEKI_DA_HOME/runtime/0.1.0-beta.7/packs/skills/`にあり、通常のホスト探索先には置きません。必要な時にだけ検索・取得できます。

```bash
python3 install.py skills list research
python3 install.py skills show researching-with-sources
python3 install.py skills export developing-story-worlds /明示的な取得先
python3 install.py skills main /メインフォルダ/.agents/skills
python3 install.py persona pack
```

スキルは参照ファイルまでコピーします。10〜20個はKisekiが案件に配置する数であり、ユーザー共通スキルや別pluginを含むホスト一覧の総数ではありません。配置されていても外部ツールや接続は`not_checked`であり、実行可能とは判定しません。

既に180個をユーザー共通の探索先に入れている環境では、そのままでは子にも共通分が見えます。移行コマンドは全ファイルのhashが原本と一致する非選択分だけを退避します。編集済み、追加ファイルのあるもの、無関係なものは保持して報告します。退避先は探索ディレクトリ外を指定します。

```bash
python3 install.py skills migrate --visible /ユーザー/.codex/skills --archive /ユーザー/kiseki-skill-archive
python3 install.py skills migrate --visible /ユーザー/.codex/skills --archive /ユーザー/kiseki-skill-archive --apply
```

最初のコマンドは書き込みなしで移行対象を提示します。適用後のバックアップとjournalは退避先に残ります。保持された編集済みスキルがあれば、Kisekiの見える総数は18個より多くなります。子を開いた後はホストの一覧で実際の公開対象を確認してください。

## サブDA

`concise`（短く率直）、`warm`（親しみやすい）、`formal`（丁寧）の3つを用意しています。`packs/personas/*.json`または別のpersona JSONを編集して指定できます。設定項目はメインと同じ8項目＋200文字以内の自由記述で、既存validatorを通します。キャラクター設定で権限・承認・記憶・完了条件は変わりません。

## 検証の範囲

生成・案件分離・親からの独立・失敗復旧・タスクの証拠付き完了は自動テストで検証します。Codex同梱app-serverの設定マージと`skills/list`はモデル呼出しなしで実測するテストを用意しました。

```bash
python3 scripts/check_project_implementation.py
```

実アプリの信頼確認後の連続対話、Claudeのnative設定マージ、翌日の文脈の十分さ、実token量と性能は別の観測項目です。ソースのテスト成功は公開済みversionや稼働中の設定への適用を意味しません。
