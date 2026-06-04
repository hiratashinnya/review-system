# 07. AI 入力設計（レビュー時の LLM 入出力）

レビュー実行時に LLM へ「何を渡し・何を返させるか」の設計。これが MVP の中核。
対象は**役割①レビュー時の LLM**（文書＋合成基準 → 指摘）。役割②（合成前の本文矛盾チェック）は
[schema「役割分担」「スコープ内マージ」](../schema/README.md) を参照。

## 原則（2軸からの帰結）

LLM の仕事は **「観点違反の発見＋`rule id` 付与＋修正原案」だけ**。仕分け（深刻度×対応モード）はしない。
ここから入力設計が決まる：

- **routing 用メタ（`severity` / `determinism` / `override`）は入力に載せない。** LLM に渡すと自己仕分け・
  バイアスの原因になる。載せるのは `rule_id` / `title` / 観点本文 / 良い例・悪い例 だけ。
  → 深刻度や適用モードは、出力の `rule_id` を使って**プログラムが後段で**付与する（[02](02-evaluation-and-triage.md)/[03](03-auto-fix-policy.md)）。
- **`rule_id` は与えた集合から選ばせる。** 該当しない指摘は捏造 id を付けさせず**未分類**へ（[Q7](../dashboard.md)）。
- **修正原案は出せる範囲で常に出させる。** 適用するか提示に留めるかはプログラムがモードで決める（LLM は判断しない）。

## 入力の構成（プロンプト）

| 区分 | 中身 | 備考 |
|---|---|---|
| 役割・制約（system） | 上記原則。「id は一覧から選ぶ／無ければ unmatched へ／仕分けはしない」 | 固定文 |
| 観点パック | 合成済み基準の各ルール：`rule_id` / `title` / 観点本文 / 良い例・悪い例 | `doc_type×scope` で継承・union 合成済み（[01](01-criteria-files.md)/schema）。provenance は内部保持で入力には不要 |
| 評価対象 | 関連文書群（1〜N ファイル）＋識別情報（ファイルパス・行番号 or 引用可能な形） | 単位は [08](08-intake-design.md)（Q12） |
| 参照コンテキスト | 上流成果物・前提条件（仕様/要件/アジェンダ等）。突き合わせ用と**ヒント程度に示す** | 任意。網羅性/整合性/前提逸脱の観点はこれに依存（I-13 / [08](08-intake-design.md)） |
| 出力スキーマ指定 | 下記 JSON を強制（structured output） | — |

> 評価対象と参照コンテキストは分けて渡すが、**LLM に「参照を指摘するな」を厳密強制しない**（守らせるのは難しい）。
> 代わりに**レポート生成時に location で機械的に除外**する：参照コンテキスト由来のファイルを指す finding は落とす。
> そのために**全 finding に対象箇所（`location.file`）を必須**で出させる。これが下記スキーマの前提。

## 出力の構成（構造化 JSON）

```json
{
  "findings": [
    {
      "rule_id": "react-component-naming",
      "location": { "file": "src/UserCard.tsx", "line_range": [1, 1] },
      "quote": "function userCard() {",
      "rationale": "コンポーネントが camelCase。PascalCase にすべき。",
      "suggested_fix": "function UserCard() {"
    }
  ],
  "unmatched": [
    {
      "description": "i18n されていない日本語文字列が直書きされている",
      "location": { "file": "src/UserCard.tsx", "line_range": [4, 4] },
      "suggested_fix": null
    }
  ]
}
```

- **`location.file` は必須**（findings/unmatched とも）。これが無いと参照除外も提示もできない。
  `line_range`/`quote` は可能な範囲で（行番号が取れない形式なら quote で代替）。
- `severity` / `mode` は**含めない**（プログラムが `rule_id → determinism×severity → ポリシー` で付与）。
- `unmatched` は「観点としては妥当そうだが既存 id に当たらない」指摘の受け皿（Q7）。
  育成ループ（[04](04-feedback-loop.md)）で新ルール候補の素材になる。

## 後段との接続

```
LLM 出力(findings/unmatched)
   │ ① 参照除外：location.file が参照コンテキスト集合に属する finding を落とす
   ▼
findings  ── rule_id でメタ参照 ──▶ determinism×severity×ポリシー ──▶ 🤖/✋/💬（O-1..O-5）
unmatched ─────────────────────▶ ❓未分類（第4区分・O-7 / Q7）
```

参照除外はプログラムが **location.file → (評価対象 / 参照) の所属判定**で行う（intake が両集合を把握している）。
LLM が参照を指摘してしまっても、ここで機械的に除外されるので問題ない。

**Q7 確定**：未分類は破棄せず**第4区分「❓ 未分類」としてレポートに surfacing**。
`rule_id` が無いので自動仕分け（🤖/✋/💬）には乗せず、人の確認用＋新ルール候補（育成 O-12）として扱う。

## 具体例（frontend スコープの合成基準で）

入力（観点パック・抜粋）：`naming-convention`（org 継承）, `react-component-naming`, `hooks-rules`（[react ファイル](../schema/examples/code.team-frontend.react.md)）。

評価対象（悪い例）:
```tsx
function userCard() {            // L1
  if (cond) {                    // L2
    const [open, setOpen] = useState(false);  // L3: 条件分岐内でフック
  }
}
```

期待される出力（要点）:
- `react-component-naming` … L1 `userCard` が camelCase → `UserCard`
- `hooks-rules` … L3 条件分岐内の `useState` → フックはトップレベルへ

プログラムはこの2件に対し、`hooks-rules`(error/deterministic) と `react-component-naming`(warning/deterministic)
のメタとポリシーを引いて 🤖/✋/💬 に振り分ける。LLM はここまで一切関与しない。

## 入力が大きいときの扱い

- **観点パック（Q18 確定）**：**MVP は全部載せ**（`doc_type` で既に絞られる）。スコープに数百ルール付いて
  膨張する場合の retrieval 的な事前選別は MVP 後の最適化として後付けする。
- **評価対象**：単位（[08](08-intake-design.md)/Q12）とチャンク戦略に依存。関連文書群をまとめる単位なら自然に収まりやすい。
