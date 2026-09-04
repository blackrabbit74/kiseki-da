# Security Policy

## Supported version

公開後は最新のbetaまたはstable releaseだけをセキュリティ修正対象とします。公開前のsupport matrixはREADMEとrelease notesが正本です。

## Reporting

公開後はGitHub Security Advisoriesのprivate reportを利用してください。秘密や個人情報をpublic issueへ投稿しないでください。

## Boundaries

- キャラクターは呼称・文体・説明量・任意提案だけを変更し、権限、承認、記憶、検証、完了判定を変更しません。
- hookはguardrailであり完全なsandboxではありません。Claude Code / Codex本体のpermissionとsandboxを併用してください。
- hookはfail-openです。壊れたhookを安全境界とみなさず、`kiseki-da doctor`とhostのhook画面で稼働状態を確認してください。
- Codexのplugin hookは利用者が`/hooks`で現在のhashをtrustするまで実行されません。
- installerはhostの承認・sandbox設定を既定では変更しません。明示的なhardeningを選んだ場合だけ、backupと差分確認後に変更します。
