# docidx — 設計経緯・移行履歴（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/docidx/SKILL.md` であり、本文は format の移行経緯と背景を保管する。

## v1 / v2 の分離

旧 doc-system v1 は巨大な Markdown にノードを埋め込む形式だったため、1ノードの照会でもファイル全体を読むコストがあった。軽量 index を先に作り必要なノードだけを読む、という `docidx` の設計はこの問題への対応である。

doc-system v2 は 1 ノード 2 ファイルの構成になり、グラフ照会を `dsv2` が担当する。v1 用実体は issue #172 で `archive/docidx-v1/` へ退避し、共有 YAML reader は `dsv2/nodeyaml.py` へ分離した。v2-native の照会役は issue #173 で `dsv2-lookup` に改名した。

これらの移行理由や旧名は履歴であり、現在の v1/v2 の使い分け・read-only 契約は skill 本文だけを参照する。

