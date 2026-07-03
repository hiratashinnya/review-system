**前提条件**: 著作エージェントが規約準拠ノードを `tmp/sprint-1/<parent-id>.md` に出力済みで、検証エラーがない。
**入力/トリガ**: 著者が reconciliation エージェントに tmp 出力の反映を依頼する。
**期待動作**: 検証を通過した tmp 出力に対し、reconciliation は当該ノードを本ファイルに転記する。
**例**: `tmp/sprint-1/fr-11-13-14.md` の FR-13 ノードが検証通過 → reconciliation が `doc-system/02-what/01-fr.md` に当該ノードを転記する。
