# test-strategy — 設計経緯・却下案（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/test-strategy/SKILL.md` であり、本文はテスト資産の運用決定と変更理由を保管する。

## TD/TC/TR 三点セットの採用

review-system のテストでは、設計（TD）、実装（TC）、実測結果（TR）を同じ識別子で追跡できる必要がある。TR に result と log_ref、実装 commit と実行環境を残すことで、失敗を隠さず、後から結果を再確認できるようにした。PF ごとの e2e も同じ対応を維持する。

## fan-out target の再試行

issue #121 以降、複数 SPEC に対する TD 著作は `authoring-fanout` に委譲している。issue #278 で retry target に `retry_of` と `error` を持たせる契約を追加したのは、再試行を新規 target として採番せず、前回の失敗 handoff と同じ対象に結び付けるためである。単一 target は直接 author を呼ぶため、fan-out に戻さない。

