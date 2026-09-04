# Privacy

Kiseki DA は外部telemetryを送信しません。対応対象のmacOS/Linuxでは、状態を`KISEKI_DA_HOME`（既定`~/.kiseki-da`）へ保存します。Windows向けコードは検証待ちであり、`v0.1.0-beta.1`の対応対象外です。

## ローカルに保存するもの

- ユーザーが確定した基本設定とキャラクター設定
- 承認済みの制約・選好・目標・事実
- タスクカード、証拠参照、候補、hookイベント
- installer transaction、バックアップ、導入版とscope

GUIから起動されたhookがcustom stateを見つけられるよう、installerは既定で`~/.kiseki-da-location`（Windowsもユーザープロファイル直下）に`KISEKI_DA_HOME`の絶対pathを1行だけ保存します。pointerが消失・破損したhookは別のdefault stateへfallbackせず、状態を読書きしないまま終了します。Pythonのuser scripts directoryにはlauncherを置き、Claude/Codexのnative plugin managerは各host自身の設定領域とplugin cacheへ登録情報・plugin copyを保存します。最終hostのuninstallでは、Kiseki DAが作成しfile kindとhashの一致を確認できたpointerとlauncherだけを削除します。Windowsではstate rootが広い読取・書込DACLを継承する場合、書込前に導入を拒否します。

通常のhook eventにはツール出力全文を保存せず、原則として対象の短い要約、成功状態、長さ、hashだけを記録します。installer journalのhost manager stdout/stderrも保存前に一般的なtoken・password・認証URL・秘密鍵形式をredactしますが、あらゆる秘密を検出できる保証はありません。復旧用transaction backupは元ファイルをそのまま保持するため、host設定ファイルに秘密があればbackupにも含まれ得ます。`KISEKI_DA_HOME`全体をprivateに扱い、秘密、API key、password、認証付きURLを設定や依頼へ入力しないでください。

## モデル提供者へ送られるもの

SessionStartで、有効な基本方針、キャラクター設定、共通制約・選好、現在プロジェクトの進行中タスク要約がClaudeまたはOpenAIへ送られます。初期設定の実モデルプレビューでも、保存前のキャラクター設定と固定テスト文が選択した提供者へ送られます。送信前にCLIが確認を表示します。

## ネットワーク

通常のhookはネットワークへ接続しません。明示的なinstall/update、実モデルプレビュー、ユーザーが依頼した外部ツールだけがネットワークを利用します。

## 削除

通常の`kiseki-da uninstall`はprofile、events、tasks、project state、transaction backupを残します。残存する`KISEKI_DA_HOME`を表示するので、完全削除は内容を確認して利用者自身が別操作で行います。v0.1には状態を自動全削除する機能を含めません。
