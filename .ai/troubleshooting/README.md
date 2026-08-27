# `.ai/troubleshooting/` — 回復手順の保管先

このディレクトリは、skill や agent が失敗・部分成功・環境制約に遭遇したときの回復手順を置く非活性の保管先です。
通常の dispatch では自動ロードされません。現在の行動契約・停止条件は skill/agent 本文に残し、ここには契約に従って停止した後の診断・回復だけを記録します。

各文書は `.ai/troubleshooting/<asset>.md` という asset-level index とし、本文の入口から必要なときだけ辿れる相対リンクを持たせます。`<asset>-<incident>.md` のような incident 単位の別ファイルは作らず、複数 incident は同じ index の見出しで分けます。新しい asset の index を追加するときは、`.ai/schema/asset-placement-v1.json` の許可リストと回帰テストも同時に更新します。設計判断、変更履歴、却下案、既知の限界は `.ai/rationale/` に置き、回復手順と混ぜません。

回復文書は次の構成を基本にします。

1. 対象の停止条件または症状
2. 事実確認（破壊的操作の前に対象を特定）
3. 安全な回復手順
4. 回復できない場合の STOP とオーナーへの報告項目
