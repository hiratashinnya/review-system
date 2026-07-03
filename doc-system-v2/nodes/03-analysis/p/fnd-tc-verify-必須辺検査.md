属性検査ビュー（D-18）から FND/TC/VERIFY ノードを抽出し、必須接続規則（D-10：must_link_to/must_be_linked_from の verification 行）に照らして必須辺の充足を確認して RULE-006 verification 違反候補を出力する。
**責務（単一動詞）**: 検証層ノード（FND/TC/VERIFY）の必須辺の欠如を検出する
**提供価値**: 検証層の接続完結性を保証し、FND が対象ノードへ、TC が仕様へ、VERIFY が TC へ接続されていることを機械的に確認できる
**入力**: D-18（属性検査ビュー・FND/TC/VERIFY と辺を含む・P-1-6 が生成）・D-10（必須接続規則・P-5-3 が生成）を消費（P→D）
**出力**: FND-TC-VERIFY 必須辺欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）
