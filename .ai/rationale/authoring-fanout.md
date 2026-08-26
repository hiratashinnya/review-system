# authoring-fanout — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/authoring-fanout.md`](../agents/authoring-fanout.md) にあり、ここは変更経緯と設計理由だけを保持する。

## fan-out を agent に分けた経緯

DD-22 の ①-C ハイブリッドは、対話入口を skill、非対話の著作 fan-out を orchestrator agent とする構成を決めた。本エージェントは、その非対話 fan-out の実体として著作担当、validator、reconciliation へ処理を渡す。委譲階層の上限は PF の実行契約に従う。旧 pipeline skill にあった「サブエージェントはサブエージェントを呼べない」という記述は、この決定と両立しないため退役した。

旧 `spec-authoring-fanout` は requirements/spec 専用だったが、issue #121 と DD23 補遺で `author` パラメータを持つ汎用 fan-out に統合した。既存の requirements-author/spec-author の挙動を壊さないことが移行条件だった。

## target key と batch nonce

`(parent_id, kind, index)` だけでキーを作ると、別バッチが同じハンドオフを上書きできる。そこでバッチ単位の nonce を共通 prefix とし、target の識別部分は従来どおり parent、kind、index とした。これにより同じバッチの target を追跡でき、batch_id も同じ nonce から導出できる。timestamp の取得はバッチで一度だけ行う。

nonce を取得できない実行環境では旧形式へフォールバックするが、既存 hand-off の存在確認を必須にして衝突を fail-close する。再試行の冪等性は nonce の再利用ではなく `retry_of` の明示で担保する。過去の nonce を今回の nonce と値比較しないのは、再試行が別時刻のバッチから来るためである。

## 変更履歴

上記のキー規則、非数字 nonce の扱い、`retry_of` の構造検査は issue #278 の F1/F2/F5 の修正を反映したもの。これらの記録は本文へ戻さず、現行の検査手順だけを本文に残す。
