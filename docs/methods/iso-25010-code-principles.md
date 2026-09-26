# ISO 25010 コード構築原則 gap 分析（Issue #539）

## 1. 判断軸と範囲

原則の採否は Issue #539 でオーナー承認済みの ISO 25010 対応を根拠とし、リポジトリの
実測で足切りしない。実測は機構化の**順番**にだけ使う。対象は `review_system/` と、
`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」に列挙された
含有されない汎用ハーネスの実装コードである。

Issue の表で一行だった「可観測性・トレーサビリティ」は対策の責務が異なるので分け、
次の7軸で gap を記録する。機能適合性は #371、性能効率性・移植性・人間向け
ユーザビリティは Issue #539 の明示的な対象外であり、本表の採否・優先順位には入れない。

## 2. 実測（優先順位の根拠に限定）

2026-09-26 の `origin/main` を対象に Python 実装を測定した。

- 対象137ファイル中、100物理行超は66ファイル。`review_system/` 単体でも36ファイル中4ファイル。
- 4行以上の連続 full-line comment は66ブロック、26ファイル。
- `@dataclass` と具体ロジッククラスの同居は5ファイル。
- repository 全体の pyright は既存記録で448 errors。一方 CI の宣言対象は
  `.github/typechecked-files.txt` の3 path に限定される。
- 互換性は `python3 -m asset_parity check` が4資産ツリーの欠落を既に fail-close 検出する。

これらは「原則を採るか」の証拠ではなく、保守性の流入・流出機構を先に置く順序の証拠である。

## 3. 7軸 gap 分析

| 軸 | 現在ある機構 | gap | 流入対策候補（書く時） | 流出対策候補（書いた後） |
|---|---|---|---|---|
| 保守性 | ヘキサゴナル構成、unittest、共通 `.ai/` 正本 | 汎用ハーネス横断の構築原則が役割契約になく、上記の定量負債がある | 実装・是正・レビュー契約に SRP/DRY/YAGNI/KISS/SSoT、テスト容易性とオーナー4原則を必須化。新規 module を100行以内で設計 | `maintainability_lint` でコメント、module、データ／ロジック分離を baseline-ratchet 検査。命名は意味判断なので reviewer が確認 |
| 信頼性 | fail-close、`retry_of`、finding 単位 commit/revert、blocker snapshot | pattern が個別実装へ散在し、新規処理の冪等性・回復性を一律に選ばせる入口と fault test がない | 処理設計 template に failure mode、再試行キー、部分成功、回復手順を必須化 | fault injection、二重実行、途中失敗後再開の共通 contract test を追加 |
| セキュリティ | role ごとの command gate、worktree isolation、workflow の最小 `permissions`、stdlib 原則 | 最小権限は個別設定。秘密情報、信頼境界、サプライチェーンの共通 review checklist と機械検査がない | role contract で権限追加理由、secret 非永続化、外部入力の非信頼扱い、依存追加審査を必須化 | secret scan、workflow permission lint、依存・action pin の supply-chain check を追加 |
| 互換性 | `.ai/` 共通正本＋薄い wrapper、`asset_parity` と CI | 機構は存在し、新規検出器は不要。ISO 対応としての位置づけが未文書化だった | 共通正本から wrapper を作る現行方式を維持 | `asset_parity` を継続。新規機構は作らず本書で役割を明文化 |
| 検証・型 | unittest、dataclass/Enum、境界 parser、限定 pyright job | typecheck 範囲外が大きく、不正状態を parse 時に型へ閉じ込める規律が役割契約にない | 境界で parse して domain type を渡す。閉じた語彙は Enum/直和、optional を下流へ漏らさない | pyright 宣言リストを clean 化した単位で ratchet 拡張。schema/境界の negative test を追加 |
| 可観測性 | stdout/stderr 分離、版 stamp、`defect_metrics`、`ci_anomaly_report` | harness 間で event schema、correlation id、silent failure の許容条件が統一されていない | logging template に event、対象、結果、version/correlation を要求 | log-contract test と「異常なのに無出力」を検出するテストを追加 |
| トレーサビリティ | Issue/PR の `Closes`、DD、karte、feedback ledger、provenance | 原則→role→check→test の対応が一箇所になく、手動記録の欠落検査も限定的 | template に Issue/DD/test の参照欄を持たせ、判断理由をコードコメントでなく DD/ADR へ置く | trace link lint と orphan 検査を追加。本書の対応表を正本として維持 |

## 4. 原則ごとの両輪

| 原則 | 流入対策 | 流出対策 |
|---|---|---|
| SOLID / SRP | 名前を付ける前に責務を一文にし、module/class を単一責務で分ける | reviewer が変更理由と依存方向を確認。module 100行 gate は多重責務の兆候を検出 |
| DRY / SSoT | 正本を一つ定め、利用側は import/reference する | parity、drift、重複定義 review で分岐を検出 |
| YAGNI / KISS | Issue の AC に必要な最小の型・分岐・依存だけを書く | reviewer が未使用 API、到達不能な拡張点、不要依存を指摘 |
| テスト容易性 | side effect を port 境界へ寄せ、決定的関数と fake seam を作る | public contract の unittest と CI |
| 命名は責務を一意に伝える | implementer/fixer が file/class/function 名から責務を読める状態で書く | 意味品質は静的推測せず reviewer が差分と実体を照合 |
| コメントは3行以内 | 長い説明が必要なら設計を分割し、経緯は DD/ADR/方法文書へ置く | `maintainability_lint` の `comment-over-3-lines` |
| module は約100行以内 | 新規 module を1スクロールで設計し、超える前に責務で分割 | `maintainability_lint` の `module-over-100-lines` |
| データ／ロジック class 分離 | データ型用 file と振る舞い用 file を初めから分ける | `maintainability_lint` の `data-and-logic-class-cohabitation` |
| fail-safe / 耐故障 / 回復 / 冪等 | failure mode、再試行 identity、transaction boundary を設計時に決める | failure injection、二重実行、再開 test |
| 最小権限 / 秘密 / 信頼境界 / supply chain | 必要な permission だけ宣言し、外部入力を data として扱い、依存追加を審査 | permission/secret/dependency/action-pin の checks |
| 型安全 / Parse, don't validate | 外部値を境界で domain type に変換し、不正状態を下流に作らない | pyright ratchet と parser negative tests |
| 可観測性 / trace | event と provenance を作成 template で必須にする | log/trace contract と orphan link checks |
| 互換性 | 共通正本＋薄い wrapper を使う | 既存 `asset_parity`。新規機構を重ねない |

## 5. 実装優先順位

| 順位 | 機構 | 理由（実測は順序だけに使用） | 本 Issue |
|---:|---|---|---|
| 1 | 共通 guidance のコード構築 checklist＋3 role contract の参照（流入） | 流入側が未明文化で、定量負債が横断的に存在。オーナー決定でも流入を優先 | 実装 |
| 2 | `maintainability_lint` baseline-ratchet（流出） | 66/137 module、66 comment block、5 mixed file を無視せず、新規・増加だけを直ちに止められる | 実装 |
| 3 | 信頼性 pattern template＋failure/idempotency contract tests | 強い個別機構はあるが横展開契約がない | 後続候補 |
| 4 | セキュリティ checklist＋secret/supply-chain checks | 権限 gate はあるが秘密・依存・信頼境界の横断 gate がない | 後続候補 |
| 5 | pyright/schema の clean-scope ratchet 拡張 | 448 error の既存負債があり、限定リスト方式を段階拡張できる | 後続候補 |
| 6 | observability event/log contract | 個別 telemetry はあるが共通 event contract がない | 後続候補 |
| 7 | trace link/orphan lint | 記録媒体は豊富だが対応関係の欠落検査が弱い | 後続候補 |
| 8 | compatibility の文書化 | `asset_parity` が既に機構を持つため、重複実装しない | 本書で完了 |

優先順位の設計判断は `docs/design/decisions.md` の DD24 に記録する。

## 6. 今回実装する境界

1位として `.ai/guidance/common.md` に唯一の原則 checklist を置き、
`.ai/agents/issue-implementer.md`、`issue-fixer.md`、`pr-reviewer.md` から参照する。
権限や dispatch は変更しない。2位として `maintainability_lint/` を追加し、CI と
`tests/unit/test_maintainability_lint.py` で検証する。

既存負債137 finding は採用免除ではない。Issue #539 の変更範囲で全分割は行わず、内容・件数を
`baseline.json` に固定して増加、編集、解消後の stale entry を fail-close にする。命名だけは
意味を機械推測すると誤検出で形骸化するため、理由を明記して role review に残す。

走査対象は repository root 直下の Python file と、Python file を含む top-level directory を
自動検出する。`tests/`、doc system、archive、仮想環境、生成物等は明示的に除外し、新しい
汎用ハーネスが静的 allowlist の更新漏れで検査対象外になる経路を作らない。
