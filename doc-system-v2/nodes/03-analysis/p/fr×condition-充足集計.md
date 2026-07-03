仕様カバレッジビュー（D-21）の FR ごとに condition 軸（normal/boundary/empty/failure/error）で SPEC と TD の充足状況を集計する。
**責務（単一動詞）**: FR×condition の充足マップを集計する
**提供価値**: カバレッジ事実の定量算出・FR ごとに何が揃い何が欠けているかを数値で把握できる
**入力**: D-21（仕様カバレッジビュー・FR/SPEC/TD と condition 属性・refines 辺を含む）・D-13（condition 語彙・網羅規則）を消費（P→D）
**出力**: FR×condition 充足マップ（P-3-2-2 へ渡す中間データ）を生成
**トリガ**: E-1 に依存（P→E）
