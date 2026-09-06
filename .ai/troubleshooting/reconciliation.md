# reconciliation — 回復手順（非規範）

`VALIDATION_OK` の欠落、parent 集合不一致、tmp 対の欠落、self_fix の確定値不在があれば、コーパスへ書き込まず blocked として hand-off を残す。バッチの一部だけを反映したり、validator の代わりに内容を修正したりしない。

反映後に clean-tmp が失敗しても手作業で広い範囲を削除しない。どの parent を反映したかと掃除失敗を記録し、保護名・symlink・階層を確認したうえで主文脈へ報告する。FND の辺を手で反転せず、dsv2 reverse の dry-run と apply の順で再開する。
