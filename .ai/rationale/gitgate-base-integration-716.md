# Issue #716: PR base の先端照合

対象: https://github.com/hiratashinnya/review-system/issues/716

現行契約は `docs/tools/gitgate-base-integration.md`（policy 2.1）。

PR #682 では PR API の `base.sha` と実際の base branch の先端が異なり、旧実装が両者を同一視したために base の取り込みを開始できなかった。policy 2.1 は、この差を許容し、PR の base ref に対応する現在の先端を branch API と fresh fetch で照合する MINOR 改訂である。

開始時の base ref を進行中記録へ保存し、continue 時の retarget を検出する。policy 2.0 の進行中記録には ref がないため、2.1 では続行せず abort で退避・中止してから再開する。
