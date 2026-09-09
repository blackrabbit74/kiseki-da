# Kiseki DA

**メインDAと考え、決めた仕事を専用DAのいるプロジェクトへ。**

Kiseki DA（Digital Assistant）は、Claude Code / Codexに、案件ごとの文脈、承認制の記憶、証拠付きタスク管理、キャラクター設定を加える個人AIハーネスです。日常の相談から、必要なスキルと初期文脈を持つ作業環境の作成・再開までを支えます。Python 3.11〜3.14の標準ライブラリで動き、外部telemetryはありません。

> **ソース版 0.1.0-beta.10 — Windows運用フィードバック**。PowerShellの誤停止、CLIの起動・証拠照合、Windows用の更新経路を修正しています。Windows 11 nativeは試験運用中です。タグ付き公開版はv0.1.0-beta.8です。

## できること

| 機能 | 使い方・動作 |
|---|---|
| メインDAとの相談 | 雑談、調査、意思決定から、タスク化・プロジェクト化する範囲を決める |
| 独立したプロジェクト | 目的・範囲、担当DA、10〜20スキル、出典・日付付きの初期文脈を指定して作る |
| 固定版の基盤 | 生成時のruntimeと案件専用stateを子に配置。親の更新や移動に依存せず再開できる |
| サブDA | `concise`・`warm`・`formal`の3プリセット、または自分のpersona JSONを選ぶ |
| 180スキルの保管庫 | 常用18個を選び、専門スキルは必要なときに検索・取得して案件へ配置する |
| 文脈と記憶 | 記憶は案件内を既定とし、承認を経て保存。共通化には利用者の明示指示が必要 |
| 証拠付きの完了 | タスクの完了条件を、読取・テスト・コマンド結果などの証拠と照合する |

各作業場所の担当DAは1人です。サブDAは継続して割り当てるキャラクター設定で、一時的な並列ワーカーとは役割が異なります。話し方を変えても、権限・承認・記憶・検証・完了条件は変わりません。

## インストール

macOS、Python 3.11〜3.14、CodexアプリまたはClaude Code / Codex CLIが必要です。Codexアプリの同梱CLIも自動検出します。利用するフォルダはGitリポジトリでなくても構いません。

```bash
git clone --branch v0.1.0-beta.8 --depth 1 https://github.com/blackrabbit74/kiseki-da.git
python3 kiseki-da/install.py install --host codex --scope user
```

Claude Codeへ導入するなら`--host claude-code`、両方なら`--host all`を指定します。初回の利用者情報とキャラクター設定を確認し、導入後に実行します。

```bash
export PATH="$HOME/.kiseki-da/bin:$PATH"
kiseki-da doctor
```

`export`は現在のターミナルだけに適用されます。常用する場合は自分の`~/.zshrc`へ追加してください。既定の状態領域は`~/.kiseki-da`で、`KISEKI_DA_HOME`で変更できます。

Codexアプリを再起動し、作業フォルダを`Local`で開きます。`/hooks`でKiseki DAのhookを確認・trustした後、`kiseki-da doctor --confirm-codex-trust`で確認済みとして記録してください。インストーラーは信頼操作を代行しません。Claude DesktopはCodeタブのlocal sessionを使用します。

### 既存環境の更新

**beta.6以前からは、初回だけ新版のインストーラーで更新してください。** 旧版の更新処理には保管パックのコピーがないためです。次のコマンドは既存の利用者設定を引き継ぎます。

```bash
git clone --branch v0.1.0-beta.8 --depth 1 https://github.com/blackrabbit74/kiseki-da.git kiseki-da-beta8
python3 kiseki-da-beta8/install.py update
```

beta.7以降を導入済みなら、通常のCLIで更新できます。

```bash
kiseki-da update --dry-run
kiseki-da update
kiseki-da version
kiseki-da doctor --json
```

更新は個人状態と実行中セッションの旧hook cacheを保持します。新版を使うときは新規セッションへ切り替えてください。**180個を共通スキルフォルダへ配置済みの場合は、下のスキル移行も別途実行します。**

[導入・更新・rollbackの詳細](docs/INSTALLATION.md) ／ [プライバシー](PRIVACY.md)

### Windows 11での試験運用

Windowsの実運用で見つかった不具合をmainへ反映しています。Python 3.11〜3.14、Claude CodeまたはCodex CLIが必要です。PowerShellで次を実行します。GUIアプリでPythonが見つからない場合も、インストーラーが実行中のPythonをlauncherへ固定します。

```powershell
git clone --branch main https://github.com/blackrabbit74/kiseki-da.git
cd kiseki-da
py -3 install.py install --host all --scope user --source .
```

既存環境は、新しいソースを取得してから更新します。

```powershell
git pull --ff-only
py -3 install.py update --source . --restart-update --dry-run
py -3 install.py update --source . --restart-update
& "$env:USERPROFILE\.kiseki-da\bin\kiseki-da.cmd" version
& "$env:USERPROFILE\.kiseki-da\bin\kiseki-da.cmd" doctor --json
```

`--restart-update`は旧runtimeと対象pluginのcache・登録情報をバックアップし、ホストの正規plugin managerで新版へ切り替えます。適用後は両ホストで新規セッションを開始してください。旧セッションの継続動作は保証しません。Codexがhookの信頼確認を求めた場合は、利用者が内容を確認します。記憶・人格・証拠・未検証記録は引き継ぎます。

保守中にKiseki DAを無効化していた場合は、再有効化を意図するときだけ更新コマンドに`--enable-plugin`を追加します。指定しない限り、無効なpluginを自動で有効にしません。

同一versionへの上書きは行いません。通常の`kiseki-da update`はGitHubのタグ付きreleaseを対象にするため、mainの試験版には上記の`--source`付き手順を使います。従来のatomic cache交換を使う稼働中更新はWindowsでは未対応です。

今回の修正では、PowerShellの`&`付きCLI、正式launcher、`Get-Content`、引用内の`release|deploy`を正しく扱い、必須制約の取得や保留がガードで止まる問題を修正しました。R1の未完了カードは注意喚起と記録に留め、完了証拠の照合とR2/R3の確認は維持します。

Python試験、分離環境の実PowerShell、Claudeのモデルを呼ばない起動、Codex plugin manager、更新・復元を検証対象にしています。実アプリの連続対話・翌日の文脈品質・Windowsの性能保証は未検証です。Bash経由のhook呼出は約1.7〜3.5秒（並行試験を含む）を観測しており、macOS向け300ms目標の達成とは扱いません。[保守と復元の手順](docs/MAINTENANCE.md)

## 専用DAのいるプロジェクトを作る

メインで合意した目的・範囲を、次のような`child.json`へ保存します。初期文脈には、その案件で必要な項目だけを出典と日付付きで指定します。

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
  ]
}
```

```bash
kiseki-da project create /絶対パス/調査レポート --answers child.json --dry-run
kiseki-da project create /絶対パス/調査レポート --answers child.json
kiseki-da project show /絶対パス/調査レポート
```

`--dry-run`は書き込みなしで作成内容を表示します。既存フォルダも指定できますが、生成対象が既にある場合は上書きせず停止します。作成後は、そのフォルダをアプリの`Local`で開くか、フォルダ内で`codex`／`claude`を起動し、ホストが求める信頼確認を行います。

案件のCLI操作には、その案件の入口を使います。

```bash
python3 .kiseki/entry.py task list --sid 現在のsession-id
python3 .kiseki/entry.py persona show --sid 現在のsession-id
python3 .kiseki/entry.py search 検索語 --sid 現在のsession-id
```

`.kiseki/`には、目的・範囲とversion/hashを記録したmanifest、固定版runtime、案件専用state、初期文脈を保存します。初期文脈の引き渡しだけで承認済みの長期記憶を作ることはありません。親子の自動同期や仕事の自動分割は行いません。

CLIの保存先権限は`access`、起動文脈と追加の指示候補は案件の`context-audit`で確認できます。既存案件への案内更新も含めて、[権限エラーからの再開と文脈の維持手順](docs/CLI-CONTEXT-MAINTENANCE.md)を参照してください。

既存の`project add`は、登録したフォルダだけで共通インストールを有効にする操作です。`project create`は、固定版基盤と独立stateを持つ作業環境を生成します。新しいメイン用フォルダも、`project create --role main`で`skills`を省略すると常用18個で作れます。

[作成・再開・失敗時の復旧と生成物の詳細](docs/PROJECTS.md)

## 常用18スキルと保管180スキル

180スキルは、相談・調査・文章作成・設計・開発・検証・運用などの手順をまとめたパックです。常用18個はその部分集合で、相談、意思決定、文脈整理、計画、検証を中心に選んでいます。全180個は`KISEKI_DA_HOME/runtime/0.1.0-beta.8/packs/skills/`に保管し、通常のホスト探索先には一括配置しません。

```bash
kiseki-da skills list research
kiseki-da skills show researching-with-sources
kiseki-da skills export developing-story-worlds /明示的な取得先
kiseki-da skills main /メインフォルダ/.agents/skills
```

`skills main`は常用18個を指定先へ配置します。子には選択した10〜20個を関連ファイルごと配置します。この数はKisekiが案件に配置する数で、ユーザー共通スキルや別pluginを含めたホストの一覧総数ではありません。外部ツール・アカウント・接続が必要なスキルの実行可否は、使用時に確認します。

すでに180個を共通探索先へ置いている場合は、次の順で移行できます。

```bash
kiseki-da skills migrate --visible "$HOME/.codex/skills" --archive "$HOME/kiseki-skill-archive"
kiseki-da skills migrate --visible "$HOME/.codex/skills" --archive "$HOME/kiseki-skill-archive" --apply
```

最初のコマンドで対象を確認し、`--apply`で原本の全ファイルhashが一致する非選択分だけを退避します。常用18個、編集済みのもの、無関係なスキルは保持し、退避先にバックアップとjournalを残します。Claude側に共通配置している場合は、その探索先を`--visible`へ指定してください。

[スキルの境界と常用セット](skills/README.md)

## サブDAを選ぶ

| プリセット | 表現 |
|---|---|
| `concise` | 短く率直 |
| `warm` | 親しみやすい |
| `formal` | 丁寧 |

```bash
kiseki-da persona pack
kiseki-da persona pack warm
```

`project create`の`persona`へプリセット名、または独自のpersona JSONのパスを指定します。設定項目はメインと共通の8項目＋200文字以内の自由記述で、同じvalidatorを通ります。[プリセット原本](packs/personas)を出発点に変更できます。

## タスクと検証

`task`、`search`、`candidate`、`approve`、`reject`、`remember`、`report`などをCLIから利用できます。方針は`kiseki-da policy show verification`で確認します。複数のClaude/Codexセッションを同時利用する場合は、SessionStartに表示された`--sid`を各操作へ付けてください。

Codexが通常のPostToolUseで終了コードを渡さない場合、その結果は完了証拠として採用しません。`kiseki-da verify run --sid 現在のsession-id -- <command> [args...]`で検証を実行すると、終了コード付きの証拠を記録できます。

ソースからの回帰テストとsmokeは次で実行します。

```bash
python3 scripts/check_project_implementation.py
```

プロジェクト生成・案件分離・親からの独立・復旧・証拠付き完了を自動テストの対象にしています。Codex同梱app-serverの設定マージとスキル発見にはモデルを呼ばない検証もあります。実アプリで信頼確認した後の連続対話、Claudeのnative設定マージ、翌日の文脈品質、実token量・性能は未検証です。

## 対応範囲と資料

- Host: Claude Code `>=2.1.142`、Codex `>=0.151.0`
- OS: macOS local。Linux localとWindows 11 nativeはbeta観測中（Windowsはmainのソース版から導入）
- App: Codexの`Local`、Claude DesktopのCodeタブのlocal session
- 対象外: WSL2、cloud session、Codex管理Worktree、Cursor、無人実行

[アーキテクチャ](docs/ARCHITECTURE.md) ／ [変更履歴](CHANGELOG.md) ／ [リリース判断](docs/RELEASE-DECISIONS.md) ／ [脆弱性の連絡](SECURITY.md)

作者: Navigator / License: MIT
