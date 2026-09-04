# Changelog

## 0.1.0-beta.1 - Unreleased

- pa-harnessをKiseki DA（Digital Assistant）として再構成。
- Claude Code / Codexのdual-manifest plugin packagingを追加。
- transaction、rollback、doctorを備えた公開installerを追加。
- schema 2の小さなキャラクター設定とproject scopeを追加。
- `KISEKI_DA_HOME`と明示的な旧`PA_HOME`移行を追加。
- macOS localをbeta.1対応対象とし、Linuxはbeta観測、Windows 11 / WSL2は検証待ちの対象外として整理。
- 複数host sessionのSID混線防止、実plugin cacheの5 hook smoke、設定変更transactionを追加。
- release gateをversion・commit・tree・最終利用者承認へ結合し、validator・CI・persona品質はbeta観測へ移行。
- 未監査のbackground資料を公開treeから除外し、Codex AppはLocal限定と明記。
