**前提条件**: ヘッダ行が出力済みで、各 FR を 1 行として明細を出力する文脈である
**入力/トリガ**: ある FR の condition 別 SPEC 充足状況を 1 行として出力する
**期待動作**: FR 1 件につき `{FR-id} | {セル} | {セル} | {セル} | {セル} | {セル}`（列順 normal/boundary/empty/failure/error）を 1 行出力し、各セルは当該 FR にその condition の SPEC が存在すれば `✅`、不在なら `⬜` とする。
**例**: FR-1 に normal/empty/failure/error の SPEC があり boundary がない場合 → `FR-1 | ✅ | ⬜ | ✅ | ✅ | ✅`。
