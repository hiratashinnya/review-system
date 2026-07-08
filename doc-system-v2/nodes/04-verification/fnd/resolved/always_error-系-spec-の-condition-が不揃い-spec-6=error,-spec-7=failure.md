**深刻度**: INFO
**内容**: RULE-007（存在しない ID 参照）と RULE-005（孤立）はともに always_error だが、対応 SPEC の condition が SPEC-6=error・SPEC-7=failure と不揃いになっている。同じ always_error 性質のルールで condition 軸の付与基準が一貫していない。
**推奨**: always_error 系 SPEC の condition 付与基準（error か failure か）を統一定義し、SPEC-6/7 を整合させる。オーナー判断。
**対応内容**: DD「SPEC-6-1 の condition を failure へ是正」に従い、SPEC-6-1（`存在しない-id-参照を-rule-007-error-報告`）を `condition: failure` へ変更した。always_error は condition とは別軸であることを config/FORMAT/notation/agent 資産に明文化した。SPEC-6-1 を verifies する TD は現行 v2 コーパスに存在しないため、RULE-019 の追随変更は不要。
**対応状況**: resolved（2026-07-08・Issue #78 follow-up）
**指摘時 ref_version**: SPEC-7 "0.2"（ノードバッジ x.y 基準・DD-8）
