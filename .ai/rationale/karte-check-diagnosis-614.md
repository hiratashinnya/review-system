# #614：是正担当の診断責務と PR の未解消判定

## 判断の理由

`status` は PR の未解消を、`check` は是正担当の診断網羅を扱う。
#503 の共通未解消集合は維持し、担当外判定は `check` 専用述語へ分離する。
`harm: none` の未解消を `status` から除外すると 2026-09-07 オーナー判断を覆すため、行わない。

自己申告の `deferred` は #683 の handoff 検証を迂回するため除外しない。
既存 `is_stall_exempt` の記録状態とハッシュ・行き先整合を採用する。
`waived` は #523 の owner override 記録が妥当な場合だけ診断対象外。
`fix-here` の主文脈担当は `scope` や `disposition` の値を増やさず、
主文脈専用 `decide` の `diagnosis_owner: main` で明示する。
担当を外しても unresolved / STOP は解除しない。

## 検証と既知の制約

`is_stall_exempt` は検証済み手渡し記録の整合をローカルに照合する。
GitHub Issue の最新状態を再取得しないため `handoff-recheck` を省略してはならない。
FBK 記録が当該 finding の判断内容と意味的に一致するかの保証は
既存 #523 の範囲を超える。`diagnosis_owner` 自体は外部承認の真正性を証明しない。

旧台帳の `diagnosis_owner` 欠落は `fixer` と解釈し、既存機能を維持する。
#745 の K-01〜K-04 が既に分割したモジュールへ局所的に追加し、
新規負債を作らず baseline 更新は行わない。
