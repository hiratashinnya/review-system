**status: open**

**保留事項**: DD-10 で確定した SRC シンボル適格性（`src_symbol_eligibility`）は **Python を前提**にしている。すなわち `source.kind` 語彙（module/class/function/method/file）も、それを判定する AST 解析（`ast` モジュール等）も Python ソースを担体とする前提で組まれる。他言語（TypeScript/Go 等）のソースを SRC 化する場合、言語別に `source.kind` の抽出手段と語彙対応を切り替えるか、言語非依存の抽象で表現する拡張が必要になる。この多言語対応を本 PEND として保留する。

**含める論点（DD-10 §決定3 からの切り出し）**: 論点1（sprint-1 スコープ）では設計種別×`source.kind` の**単純な kind 一致**で確定し、`dm=[class]`・`port=[class]` の `class` 重複を許容した。`class` 適格性の**厳密化**——Protocol（PORT の担い手）か dataclass（DM の担い手）かを AST から判別し、DM 辺には dataclass 系・PORT 辺には Protocol 系のみ有効カウントする等——も本 PEND に含める（これも Python の型構文解析に依存するため多言語拡張と同根）。

**現状（sprint-1 の到達点）**: 単純 kind 一致（`class` は DM/PORT 双方に有効）＋ Python 前提の `source.kind` 語彙で機械判定する。多言語・class 厳密化は未着手。

**影響要素**: `接続ルールスキーマ`（`src_symbol_eligibility` のスキーマ・語彙定義を多言語/厳密化へ拡張する対象）。起源＝DD-10。

**実施時期はオーナー判断**: 本 PEND の `scheduled` は起票時点＝`sprint-1`。実施 sprint を独断で未来へ繰り越さない（CLAUDE.md「スケジュール独断禁止」）。多言語対応・class 厳密化を今スプリントで着手するか後続へ回すかはオーナーが決める。

**配置（open）の理由**: 本 PEND を `deferred` に置くとスプリントの後ろ倒しを独断で決めたことになるため `open`（未処置の保留項目）とする。DD-10 は本項目を「決定スコープ外の将来拡張」として切り出したのみで、実施時期の繰り越しまでは確定していない。
