# Issue #158「本文resolved済みopen FNDをlifecycle上もresolvedへ整理する」

- URL: https://github.com/hiratashinnya/review-system/issues/158
- 状態: closed（2026-11-18取得）
- 本文: 465文字/ 19行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: なし
- PR参照: なし
- 主見出し: なし
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - open FND の中に本文上は resolved 済みのものが残っている。
- - 具体例: `_drift` の z バンプ誤検出、`backref check` の open-but-backref 判定トートロジー。
- - Sprint 1 では、明示 defer されていない FND は open のまま残さない。
- - 対象 FND が `fnd/open` から消える。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
