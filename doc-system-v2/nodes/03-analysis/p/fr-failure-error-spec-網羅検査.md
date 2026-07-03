属性検査ビュー（D-18）から FR ノードを抽出し、FR 配下に condition: failure または condition: error の SPEC が存在するかを coverage_rules（D-13）に従って確認して RULE-018 違反候補を出力する。
**責務（単一動詞）**: FR 配下の failure/error SPEC の欠如を検出する
**提供価値**: 異常系仕様の欠落を可視化し、FR が failure/error 条件の仕様を持つことを促進できる
**入力**: D-18（属性検査ビュー・FR/SPEC と condition 属性を含む・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**出力**: FR failure-error SPEC 欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）
