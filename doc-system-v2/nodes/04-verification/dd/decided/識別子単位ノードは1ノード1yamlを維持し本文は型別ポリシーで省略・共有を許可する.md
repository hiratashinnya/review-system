**論点**: 実装層 SRC と検証層 TD/TC は、要件・分析・設計層と同じ「1ノード=本文Markdown+サイドカーYAML」の物理形では冗長または不十分になる。特にコードは関数・クラス等の識別子単位で追跡したいが、1関数1Markdown本文は保守不能である。

**決定**: ノード粒度は識別子単位を許容しつつ、サイドカーは全型で **1ノード1YAML** を維持する。本文 Markdown は型別ポリシーに分離し、SRC と TC は本文なしを許可し、TD は複数 TD ノードが1つのテストプログラム単位 Markdown 本文を共有できる。

**決定内容**:

1. **共通原則**: YAML は node identity / version / condition / labels / scheduled / edges / 実体参照を持つ正本であり、1 YAML に複数ノードを詰め込まない。
2. **SRC**: 1 関数・1 class・1 public method 等の識別子を 1 SRC ノードとする。SRC は source code 自体を本文実体とみなし、Markdown body を持たない。YAML は `source.file`・`source.qualname`・`source.kind` 等でコード識別子を指す。
3. **TD**: 1 TD は1テスト設計シナリオを表す。複数 TD が同一テストプログラムファイル単位の Markdown body を共有してよい。各 TD YAML は `body_ref.file` と `body_ref.anchor` で共有本文内の該当節を指す。
4. **TC**: 1 TC は1テスト関数または1テストケース実装を表す。TC は Markdown body を持たず、YAML の `test.file`・`test.qualname`・`test.kind` で実テスト識別子を指す。
5. **TD-TC**: TD と TC は 1:1 とする。TD は exactly one TC から実装され、TC は exactly one TD を実装する。現行の「TD←TC が少なくとも1件」より強い制約として後続 RULE/SPEC で表現する。

**不採用**:

- **1 YAML に複数 identifier node を詰め込む node pack 案**: ファイル数は減るが、node identity / version / drift / edge / review diff が複数ノード混在になり、v2 の 1 node 1 sidecar 原則を崩すため不採用。
- **1 identifier ごとに Markdown body を作る案**: 追跡精度は高いが、実装関数・テスト関数の増加に対して本文ファイルが過剰になり、実運用で冗長になるため不採用。
- **SRC を1ソースファイル1ノードにする案**: 同一ファイル内の複数設計実現が混ざり、SRC→DM/PORT/ORC の辺が曖昧になるため不採用。

**必要な後続反映**:

- FORMAT / notation の「1ノード=2ファイル」表現を、「1ノード=1 YAML、body は型別ポリシー」に改訂する。
- `schema/sidecar.schema.json` または型別 schema に `source` / `test` / `body_ref` を導入する。
- `validate.py` / `dsv2 meta` / `rename` / `viewer` を bodyless/shared-body 方針に追随させる。
- `config.yml` に implementation 層の `src` layout を材化する。
- TD-TC exactly-one 制約を SPEC/RULE として著作・実装する。
- test-strategy / verification-author / author 系テンプレートを追随させる。

**覆る場合の影響**: 1 YAML 複数ノードを採用する場合は、meta.json の node identity、drift 判定、rename、viewer、review diff 単位を全面再設計する必要がある。1 identifier 1 Markdown を採用する場合は、ファイル増加と著作負荷を受け入れる必要がある。
