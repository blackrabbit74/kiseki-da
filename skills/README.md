# Kiseki DAのスキルパック

v0.1.0-beta.7は180スキルを保管パックとして配布し、そのうち18個をメインの常用セットに選びます。承認、状態変更、証拠照合、scope判定はCLIとhookが担います。スキルの本文やキャラクター設定は権限を変更しません。

## 常用18個

- [exploring-ideas](exploring-ideas/SKILL.md)
- [clarifying-outcomes](clarifying-outcomes/SKILL.md)
- [analyzing-assumptions](analyzing-assumptions/SKILL.md)
- [comparing-options](comparing-options/SKILL.md)
- [researching-with-sources](researching-with-sources/SKILL.md)
- [reviewing-literature](reviewing-literature/SKILL.md)
- [auditing-source-credibility](auditing-source-credibility/SKILL.md)
- [retrieving-context](retrieving-context/SKILL.md)
- [extracting-insights](extracting-insights/SKILL.md)
- [synthesizing-documents](synthesizing-documents/SKILL.md)
- [defining-product-briefs](defining-product-briefs/SKILL.md)
- [defining-domain-terms](defining-domain-terms/SKILL.md)
- [designing-experiments](designing-experiments/SKILL.md)
- [testing-concepts](testing-concepts/SKILL.md)
- [mapping-strategy](mapping-strategy/SKILL.md)
- [revising-plans](revising-plans/SKILL.md)
- [reviewing-plan-consistency](reviewing-plan-consistency/SKILL.md)
- [structuring-arguments](structuring-arguments/SKILL.md)

## 配置と取得

原本はこのディレクトリ、インストール後の保管先は`KISEKI_DA_HOME/runtime/0.1.0-beta.7/packs/skills/`です。skills list/show/exportで必要なものを取り出し、skills mainで18個を明示した探索先へ配置します。子には選択した10〜20個を関連ファイルとともに配置します。

外部ツール・アカウント・接続の利用可否は配置だけでは検証されません。実行時に必要な依存を確認してください。編集済み・無関係なスキルは移行コマンドでも保持します。

[作成・取得・共通配置の移行手順](../docs/PROJECTS.md)
