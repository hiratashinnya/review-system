# doc-system-v2-authoring — 回復手順（非規範）

schema、path、slugify、edge、version のいずれかで検証に失敗した場合は、tmp の md/yaml 対を保持し、validator の対象 field と期待値を確認する。本文へ YAML や属性を足して形式エラーを隠さない。

既存ノードの scheduled backfill で具体値が dispatch に無い場合は current phase を採用せず STOP する。対象 slug、件数、推測され得る値を hand-off に記録し、オーナーの明示値を受けてから再開する。新規ノードの default と既存値の変更を同じ一括修正として扱わない。
