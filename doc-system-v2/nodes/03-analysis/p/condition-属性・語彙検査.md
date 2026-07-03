属性検査ビュー（D-18）から SPEC/TD ノードを抽出し、condition 属性の存在と condition 語彙・網羅規則（D-13：condition_vocab）との一致を確認して RULE-016 違反候補を出力する。
**責務（単一動詞）**: SPEC/TD の condition 属性の存在と語彙の正当性を検出する
**提供価値**: condition が未設定または語彙外の値を持つ SPEC/TD を排除し、カバレッジ集計の健全性を保証できる
**入力**: D-18（属性検査ビュー・condition 属性を含む・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**出力**: condition 属性・語彙違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）
