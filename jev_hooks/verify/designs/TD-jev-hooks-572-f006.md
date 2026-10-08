---
id: TD-jev-hooks-572-f006
version: 1
condition: failure
---
# F-572-006: 現在入力/R4 contextの機密本文最小化

## 目的と前提

[独立レビュー5429570390](https://github.com/hiratashinnya/review-system/pull/571#pullrequestreview-5429570390)で、Write/Edit .envの本文がcurrent_tool_inputとskill_context.current_tool.inputからSDK HTTP bodyへ残ることを確認した。履歴tool_callsだけの除外では不十分だった。XR-571-2の外送秘密除去に属する追加findingを、F-572-005および旧60/62件証跡と分ける。

基準local commit `c961e8eb3bb000f218f20cdee281795e98d8cd6f`、同tree公開head `d648a02e8d2350a83d73218a7d6d7c91aafbb2c6`。変更はoutbound_evidence、outbound_inputs、outbound_contextと3TC moduleの計6Python file。SDK0.7.2/HTTP MockTransportでfake canaryだけを用い、実API/実秘密/settings結線を要求しない。

## 手順と期待結果

| ケース | 手順 | 期待結果 |
|---|---|---|
| I1 恒久HTTP TC | test_safety_sensitive_inputs.pyを旧版孤立git archiveと修正treeで実行。Write/Edit × run_event/R4・semantic_eval/R4の4subcase | 旧版2tests/4fail。修正後bodyに不透明canaryなし。current_tool_input/current_tool/selector/protected_operationsすべて機密inputを省略 |
| I2 通常入力 | test_safety_projection.pyで通常fileのcontent/old/new本文を配置 | pathだけ保持し本文を送らない |
| I3 shell全コピー | 同じshellを履歴/current/context/selector/protected_operationsへ配置。引数・環境代入・heredocへcanary配置 | 全コピー同じprojection。実行名/複合構造/既知git動詞/option名保持、引数値/環境代入/本文を省略。shell結果も省略 |
| I4 R3質問 | .envに言及するAskUserQuestion本文と公開chatを配置 | 質問本文を機密file入力と誤認せず、R3質問と公開chatを保持 |
| I5 統合 | SDK/stdlibのtests/jev_hooks直接discover、maintainability/time lint、diff check | SDK69PASS/skip0、stdlib69PASS/skip4、lint違反0/debt134、時刻16検出/違反0、各module100行以内 |

## 契約と限界

共通projectionは全入力コピーへ適用する。敏感file pathの入力を省略し、通常inputはquestions/query/pattern/url/file_path/path/globのみ。Bash系commandは意図の構造へ投影する。AskUserQuestionの.env言及自体は除外条件にしない。任意keyの既知秘密entry/value除去とSDK-owned schema維持（F-572-005）は保持し、実認証キーはSDK必須HTTP headerでだけ使用する。

省略した引数値・機密path・file/code本文・未解析shellの情報を推測で補わず、不十分な意味判断はunknownにする。引数やコードに依存するR4意図判定は限定される。実モデルの意味精度/誤拒否率は未評価、未知秘密完全検出保証はない。通知実配送・WSL/Claude Code実セッション・設計HTML照合は未検証。設定schema不変、同じ未merge PRの是正なので質問/ルール版1.1を維持する。

今回の6fileを使わない既存unitは反復しない。旧ローカル全unit2105件11fail/1errorのうち変更由来governance1件は修正済み、残る10fail/1errorは旧HEADでも同環境再現という既存TRを保持する。修正前d648a02のCI run37474698960は全3 checks成功。修正後headのCI/新しい独立レビューは別途確認する。
