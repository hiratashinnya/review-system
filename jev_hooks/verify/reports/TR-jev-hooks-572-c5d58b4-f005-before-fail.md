---
id: TR-jev-hooks-572-c5d58b4-f005-before-fail
version: 1
condition: failure
td_id: TD-jev-hooks-572-f005
result: FAIL
log_ref: jev_hooks/verify/logs/TD-jev-hooks-572-c5d58b4-f005-fail.txt
---
# F-572-005: 任意dictキーからの既知秘密漏れ

## 目的と前提

独立レビューで、APIキーを任意入力dictのキーへ置くとHTTP bodyへ残ることを確認した。値・自由文だけの秘密除去では満たせない境界を修正し、既知秘密/credential形式をキー文字列・動的tool IDからも除去する。XR-571-2の外送秘密除去に属する追加findingとして、旧F-572-001〜004/旧60件検証と分けて記録する。

基準はローカルcommit `c5d58b481f29ae39646f50ca79fb9614ad7cbe81`、同treeの公開head `9e930e678d6f1725ddbdffd7f33529b0713215e5`。今回のコード/TC変更はredaction.py、outbound_evidence.py、test_safety_redaction.py、test_safety_transport.pyの4file。公式SDK0.7.2とHTTP MockTransportを使い、実API・実秘密・settings結線を要求しない。

## 手順と期待結果

| ケース | 手順 | 期待結果 |
|---|---|---|
| K1 秘密キー | 既知秘密とその部分文字列を任意dictのkeyに置き、対応valueに別canaryを置く | keyと対応valueのentry全体が消える。残るcanaryなし |
| K2 credential形式/入れ子 | Authorization/Bearer/token代入形式を任意キーと入れ子へ置く | credentialキーと対応valueを除外し、list/dictの深部にも残らない |
| K3 collision | 複数秘密keyと通常の`[REDACTED]`キーを併置する | 改名せずentry除外するため通常key/valueを上書きしない |
| K4 所有schema/動的ID | schema名と同じ既知秘密を任意入力key/動的tool IDへ置く | 任意key/IDと対応value/resultを除外する。SDK所有のpublic field・tool構造・input selector・質問schema keyは維持 |
| K5 実HTTP/semantic CLI | SDK factoryをHTTP mockに差替え、JevEvaluatorとsemantic_evalの両経路で実シリアライズbodyとauthheaderを採取 | bodyの秘密key/value、自由文、質問から全canaryを除去。authheaderのみ正常な必須認証値を保持。外側assertで例外catchによる偽PASSを防ぐ |
| K6 統合 | 安全suite12件、SDK全discover62件、maintainability/diff check | 安全12件PASS、統合62件PASS/skip0、保守性違反0/accepted_debt134、変更module100行以内 |

## 範囲と限界

任意入力のkey/値をマスクする境界とSDK自身の固定schemaを区別する。未知秘密の完全検出保証はなく、独自秘密はsecret_env_varsへ宣言する。除外された証拠はunknownを増やしうる。実キーはSDKの必須HTTP認証ヘッダにだけ渡し、証拠payload/質問/状態/監査へ持ち込まない。実モデル意味精度・実通知配送・WSL/Claude Code実セッションは未検証。今回の4fileを使わない既存unitの環境依存10fail/1errorは旧TRの切分けを保持し、全unitを反復しない。

## 修正前の実測（2026-10-06）

基準local commit c5d58b481f29ae39646f50ca79fb9614ad7cbe81（公開head9e930e678d6f1725ddbdffd7f33529b0713215e5と同tree）に新回帰TCを追加した。安全suite11件は2fail: K1/K2/K3の任意dict秘密keyと対応valueが残り、K5のSDK実HTTP bodyにもAPIキーcanaryが残った。K4の専用schema/動的ID TCは修正後に追加したためこの赤段階では未実行。

[赤生ログ](../logs/TD-jev-hooks-572-c5d58b4-f005-fail.txt)。根因は値だけを処理してキーを検査しないredaction。対策は任意のキー/動的IDに秘密を含むentry全体を除外し、schema-owned keyは保持すること。マスク名への改名はしない。HTTP mockだけを使い、実API通信なし。

[修正後PASS TR](TR-jev-hooks-572-c5d58b4-f005-worktree.md)は安全12件と統合SDK62件の成功を記録する。この赤ログ/FAIL TRは上書きしない。
