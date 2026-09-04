# キャラクター設定

Kiseki DAのキャラクターは表現上の既定です。安全、事実性、現在の利用者指示、承認、記憶、検証、完了条件より常に下位です。

固定項目は、名前、一人称、ユーザー呼称、丁寧さ、温かさ、説明量、提案積極性、関係性の8つです。それ以外は200文字以内の自由記述へまとめます。自由記述は話し方・雰囲気・比喩・語尾に限定し、秘密や操作権限の指示を保存しません。

生成するキャラクターブロックは最大220推定token、全常駐文脈は最大2,500 tokenです。無設定ならキャラクターブロックは生成されません。

```text
kiseki-da setup
kiseki-da persona show
kiseki-da persona edit
kiseki-da persona edit --name "キセキ" --yes              # 保存のみ、外部送信なし
kiseki-da persona edit --name "キセキ" --yes --live-preview # 明示同意して試着
kiseki-da persona preview                                  # 保存済み設定を明示試着
kiseki-da persona reset
```

実モデルプレビューは設定をモデル提供者へ送ります。`--yes`は保存確認だけで、送信同意にはなりません。対話中の明示確認、`persona preview`、または`--live-preview`でだけ送信します。最大3回、選択した全hostで既定モデルを利用し、Kiseki DAのevents/profileには応答を保存しません。失敗時は固定プレビューへ切り替えます。
