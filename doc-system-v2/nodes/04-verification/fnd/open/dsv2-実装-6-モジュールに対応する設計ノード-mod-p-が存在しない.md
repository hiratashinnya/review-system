**深刻度**: WARNING（現時点で `validate.py` は発火しない＝設計層から実装への欠落を検査する規則が無い。ただし `current_stage: implementation` 到達後は `mod←src` 系の必須辺が発火するため、SRC を materialize しようとした時点でブロッカーになる）

**内容**: `dsv2/` に実在する実装のうち **6 モジュール**（`viewer.py` / `rename.py` / `reverse.py` / `gitutil.py` / `yamledit.py` / `dashboard.py`）について、対応する設計ノード（MOD）も、その責務を表す分析ノード（P）も in-graph に存在しない。設計層 MOD は 18 件（`parser` / `collector` / `filter` / `domain` / `config` / `reporter` / `projector` / `reconciler` / `author` / `drift_checker` / `condition_checker` / `verification_checker` / `structure_checker` / `graph_coverage` / `spec_coverage` / `ports` / `adapters-fs` / `__main__`）あるが、いずれも責務記述が `spec_inspector/*.py` の検査パイプライン分割であり、上記 6 本の責務（HTML ビューア生成・slug 改題と referrer 一括張替え・FND 辺逆転・`git mv` ラッパ・サイドカー行編集・dashboard 集計）を包含していない。P 56 件のタイトルにも「改題」「辺逆転」「HTML ビューア」に相当するものが無い。**実装が先行して設計層に反映されていない「設計外実装」**であり、`spec_inspector/*` を宣言する MOD/DM/PORT/PRS 26 件が実装を持たない指摘（C1・逆方向）と同根の乖離である。

**対象実装（6 本）と in-graph 根拠の有無**

| 実装 | 責務（docstring 実測） | in-graph の根拠 | 対応 MOD | 対応 P |
|---|---|---|---|---|
| `dsv2/viewer.py` | meta.json ＋本文 Markdown から単一 `doc_view.html` を生成（オフライン自己完結・標準ライブラリのみの最小 Markdown レンダラ内蔵） | なし | なし | なし |
| `dsv2/rename.py` | slug 改題（yaml/本文の改名＋全 referrer の `edges[].to` 一括張替え・既定 dry-run） | なし | なし | なし |
| `dsv2/reverse.py` | FND 辺逆転（forward 削除＋backward 付与＋DD-3 本文凍結＋z バンプ＋`git mv`） | **あり**（DD `fnd-専用ライフサイクルルールを-config-に独立定義…`／DD `fnd-起票時の-ref_version-本文記録ルール制度化`／DD `resolved-fnd-辺逆転-backref-付与の版バンプ種別を-z-バンプに確定…`） | なし | なし |
| `dsv2/gitutil.py` | `git mv` の薄いラッパ（reverse の status 遷移・rename の改名で共用・git 管理外は fs move フォールバック） | なし | なし | なし |
| `dsv2/yamledit.py` | サイドカー `{slug}.yaml` への行ベース最小編集（純関数・限定文法前提） | なし | なし | なし |
| `dsv2/dashboard.py` | `nodes/**` から stage/type 件数と FND/Q/DD/PEND lifecycle status の Markdown スナップショットを機械集計 | なし | なし | なし |

**本指摘の対象外（留保）**
- `doc-system-v2/slugify.py` は SPEC に根拠があるため本指摘の対象に含めない。
- `dsv2/reverse.py` は上表のとおり DD 3 件に決定根拠を持つ。ただし**決定はあるが設計ノード（MOD/P）が無い**状態であり、「決定すら無い」他 5 本とは欠落の質が異なる。処置方針を分ける余地があるため本文に区別して記録する。
- `dsv2/viewer.py` は P `依存グラフ出力処理`（post-mvp・sprint-2・dot/JSON 隣接リストをファイル出力）と近接するが、責務（静的 HTML の全ノードブラウズ UI 生成）も出力物も別であり、既存 P への包含では説明できない。
- 既存 MOD への包含可能性を実地確認した結果、`adapters-fs`（責務＝`FileSystemPort` の Real/Fake 実装）・`reconciler`（責務＝P-7-2 調停・本ファイル反映）・`reporter`（責務＝P-4 レポート生成・G# 採番・終了コード決定）・`projector`（責務＝P-1-6 検査ビュー射影）のいずれも、現行の責務記述のままでは上記 6 本を含意しない。「粒度が粗くて既に包含されている」ケースには**該当しない**。

**forward 辺の張り先と選定理由**

本指摘は「対応する設計ノードが存在しない」こと自体が内容であるため、指摘対象そのもの（欠落しているノード）に辺を張ることが原理的にできない。そこで、**欠落を受け止めるべき最も近縁の既存ノード**を各層 1 件ずつ選び、便宜上そこへ forward 辺を張る（本来の張り先は当該 6 本に対応する未著作の MOD/P である旨をここに明記する）。

1. **MOD `__main__`** — 設計層側の受け皿。責務が「合成ルート ＋ CLI エントリポイント（DI 結線・コマンドライン引数解析）」であり、**モジュール構成の集合を定義する唯一の MOD** である。モジュールが 6 本増減すれば必ずこのノードの結線記述が変わるため、「MOD 一覧に 6 本が無い」という指摘の自然な受け皿になる。個々の MOD（`reporter` 等）に張ると、その 1 モジュールの責務不足という別の指摘に読み替えられてしまうため採らなかった。
2. **P `ノード著作・反映プロセス`（P-7）** — 分析層側の受け皿。`rename` / `reverse` / `dashboard` / `yamledit` / `gitutil` はいずれも「ノードの著作から本ファイル反映まで」の活動（reconciliation が実行する機械処置）に属するが、P-7 の子は `著作・tmp-出力`（P-7-1）と `調停・本ファイル反映`（P-7-2）の 2 つのみで、改題・辺逆転・dashboard 集計に相当する子プロセスを持たない。すなわち **P-7 の分解漏れ**として指摘が成立する唯一の既存ノードである。
3. `viewer` については上記のいずれにも自然な親が無い（P の L1 にビューア生成系の親プロセスが存在しない）。3 本目の辺は張らず、本記述をもって欠落の所在の記録とする。

**選択肢**
1. **6 本それぞれに対応する MOD を新設し、必要な P も併せて起票する**（`viewer` は L1 プロセスの新設、`rename`/`reverse`/`dashboard` は P-7 配下の子プロセス、`gitutil`/`yamledit` は基盤ユーティリティ MOD として位置づけ）。設計層が実装の現況に追随し、`#160` の SRC materialize が 6 本について直ちに可能になる。一方、C1 側の 26 件（`spec_inspector/*` 前提）が未処置のまま残ると、MOD 一覧に「実装のある新設 6 件」と「実装のない既存 18 件」が併存し、モジュール分割の正本が二重化する。
2. **既存 MOD の責務記述を改訂して 6 本を包含させる**（例: `gitutil`/`yamledit` を `adapters-fs` へ、`rename`/`reverse`/`dashboard` を `reconciler` へ、`viewer` を `reporter` へ）。新設ノードが増えずグラフは小さく保たれるが、`adapters-fs` は `FileSystemPort` 実装、`reporter` は違反レポート整形という別責務を既に負っており、包含は単一責務の希薄化（PR1 違反）を招く。また `src_symbol_eligibility: mod: [module]` の下で 1 MOD に複数の Python モジュールを紐づける形になり、SRC の担体対応が 1:1 でなくなる。
3. **C1 と同じ処置単位で、MOD 一覧そのものを dsv2 の実モジュール構成へ再定義する**（`spec_inspector/*` 前提の 18 MOD を `dsv2/*` ＋ `doc-system-v2/validate.py` の実構成へ再マップし、その再マップの中で本 6 本を位置づける）。設計・実装の乖離を C1/C2 まとめて解消でき、正本の二重化も起きない。反面、影響範囲が MOD 18 件 ＋ DM 6 件 ＋ PORT 1 件 ＋ PRS 1 件に及び、`#160` の作業量が最大になる。
4. **設計層を正とし、実装側を設計に合わせる**（6 本を既存 MOD の分割に沿って再編する）。設計の一貫性は保たれるが、6 本はいずれも稼働中の機械処置（`dsv2 reverse` は CLAUDE.md 規約上の必須ツール）であり、実装の作り直しコストと退行リスクが大きい。

**推奨**: **選択肢 3 を基軸に、その内側で選択肢 1 を実施する**。根拠は 3 点。(a) 本指摘と C1 は「`spec_inspector/*` を前提にした設計層」対「`dsv2/*` として育った実装」という**単一の乖離の表裏**であり、C2 だけを先に処置すると MOD 一覧が二重化して再乖離を招く。(b) 選択肢 2 の包含は PR1（もので分ける）と `src_symbol_eligibility` の 1:1 担体対応の両方に反する。(c) 選択肢 4 は稼働中ツールの作り直しであり、オーナー方針（2026-07-26・乖離は `#160` のスコープ内で設計実装の整合を取る）が「設計変更」も選択肢に含めている以上、実装追随より設計側の再定義が先に検討されるべきである。ただし `reverse` は既に DD 3 件の決定を持つため、再マップ時にその DD からの派生として MOD/P を導出できるか（決定→設計→実装の連鎖が復元できるか）を先に確認することを併せて推奨する。**いずれの選択肢を採るか、および実施スプリントの決定はオーナー判断を仰ぐ**。

**接続規則変更の伴否**: 本指摘は `doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` の追加・変更・削除を含まない（欠落しているのはノードであって規則ではない）。したがって接続マトリクス・ドキュメント一覧・各 author エージェント/スキルへの伝播同期は不要と判断した。

**対応状況**: open

**対応 Issue**: #160（Sprint 1 対象の SRC 実装ノードを materialize する）・関連 #127（「実装は dsv2 が該当する想定だが、これまでの開発エージェントがそれを意識しておらず、仕様外実装や設計外実装が多数ある見込み」）

**指摘時 ref_version**: `__main__` "0.1"（`__main__`.yaml v0.1.0 時点）
**指摘時 ref_version**: `ノード著作・反映プロセス` "0.4"（`ノード著作・反映プロセス`.yaml v0.4.0 時点）
