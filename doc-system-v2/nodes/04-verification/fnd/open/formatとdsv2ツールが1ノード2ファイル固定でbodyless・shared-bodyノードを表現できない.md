**内容**: doc-system-v2 の FORMAT / notation / validate / dsv2 ツール群は、現状「1ノード=本文 `.md` + サイドカー `.yaml`」を固定前提としている。この前提では、DD「識別子単位ノードは1ノード1YAMLを維持し本文は型別ポリシーで省略・共有を許可する」で決定した SRC bodyless、TC bodyless、TD shared-body を表現できない。

**確認した事実**:

- `doc-system-v2/FORMAT.md` と `doc-system-v2/notation.md` は「1ノード=2ファイル」と明記している。
- `doc-system-v2/validate.py` は `nodes/**/*.md` を走査し、同名 `.yaml` 欠落をエラーにする。
- `dsv2/meta.py` は YAML 走査のため bodyless へ寄せやすいが、`body_path` を常に同名 `.md` として生成する。
- `dsv2/rename.py` は対象ノードの `.md` と `.yaml` を同時 rename する。
- `dsv2/viewer.py` は `.md` 不在時に空本文表示できるが、仕様上の body policy は未表現である。

**期待される解消**:

1. FORMAT / notation を「1ノード=1 YAML、本文は type ごとの body policy」に改訂する。
2. body policy を機械可読化する。少なくとも `required` / `none` / `shared` を表せること。
3. validator が type ごとの本文要否を検査する。
4. index / rename / viewer が bodyless/shared-body node を扱える。

**依存**: DD「識別子単位ノードは1ノード1YAMLを維持し本文は型別ポリシーで省略・共有を許可する」の反映作業。

**推奨スコープ**: 最初に FORMAT / notation / schema / validator を小さく同期し、その後 dsv2 rename/viewer へ広げる。SRC/TD/TC の具体ノード大量作成より先に行う。
