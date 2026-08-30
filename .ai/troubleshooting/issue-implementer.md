# issue-implementer — 回復手順（非規範）

dispatch marker、branch、handoff path、workspace の検査に失敗した場合は main 側へ書き込まず STOP する。作業ツリーが isolated か、期待 OID と現在の branch が一致するかを呼び出し元に確認して再開する。

テストや corpus 委譲が利用できない場合は、別の実行経路へ無断フォールバックしない。corpus は author→validator→reconciliation の hand-off を再取得し、テストはプロジェクトで指定された標準コマンドの失敗内容を報告する。
