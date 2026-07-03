**もの**: 仕様カバレッジ計測（FR×condition 充足集計）の結果を表す内部表現。各 FR がどの condition で SPEC/TD に充足されているかを集計したテーブル。違反（ViolationRecord）ではなく充足度の計測値である。
**用途**: spec_coverage（MOD-17）が D-21（仕様カバレッジビュー）と D-13（condition 語彙・網羅規則）から FR×condition 充足を集計して生成し、reporter（MOD-8）がカバレッジ点検結果（O-2）の整形に用いる。D-7（カバレッジ計測結果）の後半（FR×condition カバレッジテーブル）の型。前半（グラフ網羅性穴リスト）は ViolationRecord 列（TERM-3）が担う。
**Python 型名**: `CoverageReport`
**保持要素**: FR ごとの行（FR id・required_conditions 充足状況・recommended_conditions 充足状況・充足/未充足の SPEC/TD 参照）と集計サマリ（充足率等）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）
