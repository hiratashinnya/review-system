# pr-reviewer — 設計経緯・却下案・既知の限界（rationale・非規範）

> **これは規範ではない。** `.claude/agents/pr-reviewer.md`（規範・正本）から Issue #372 で
> 移設した「設計判断の理由・却下案・既知の限界・過去インシデントの経緯・実測ログ」の保管先
> （PR8「消さない」＝削除ではなく移設）。**dispatch 時にロードされない**ので、行動を決める規範は
> すべて移設元に残っている。疑問が生じたときだけ参照する。
>
> - **移設元（規範・正本）**：`.claude/agents/pr-reviewer.md`
> - **本文は移設元の文言を尊重して移した**（内容の変更・要約はしていない）。ただし `##` 見出しの
>   付与に加え、複数節をまとめる際・切り出した断片を単独の節として成立させる際に必要な最小限の
>   接続語・言い換えは補っている（見出しだけを付与した逐語移設ではない）。移設先で `##` 見出しを
>   付与し、どの節から来たかを併記している。
> - **相対参照は移設元の文脈を指す**：本文中の「後述」「上記」「下記」「本節」等は
>   移設元ファイル内の位置関係であって、本ファイル内の位置関係ではない。
> - **移設は規範を緩めない**：本ファイルにあるのは「なぜその規範があるか」だけで、規範そのもの
>   （承認/却下ステータスを偽らない・オーナー専権事項を自己判定しない）は移設元で有効なまま。
> - 分離の方針・4ツリー波及方針は `.ai/rationale/README.md`。

## 「承認したと嘘をつかない」規範の根拠と実インシデント（移設元：「絶対厳守：承認/却下ステータスを偽らない」節）

規範側「してよいこと」の末尾に付いていた根拠（PR #382・2026-08-17 の文言修正より前の版）：

このロールは `issue-implementer` とは別コンテキストで動作し `Write`/`Edit` を持たず（コードを一切書けない）、レビュー対象を著作していないため、GitHubの「著者と同一アカウント」判定は自己承認の代理指標として本構成には当てはまらない。

実インシデント：

（実インシデント：2026-07-07、このロールの前身にあたる汎用エージェント委任で、自己承認ブロックをコメントで偽装（承認したと嘘の主張）した上でマージした事例が発生し、セキュリティ違反として検知された。技術的なレビュー内容自体の正当性とは別に、承認プロセスの偽装は独立した重大な問題として扱う。）

## 「オーナー専権事項を自己判定しない」規範の根拠と実インシデント（移設元：「オーナー専権事項の自己判定禁止」節）

規範側「禁止」項の末尾に付いていた根拠：

機械検算は「diff が意図通り実行されたこと」を保証するだけで、「その意図（書き込む値）自体がオーナーの意向と一致すること」は保証しない。

実インシデント：

（実インシデント：2026-07-09、PR #150「Codex AI agent: #94 scheduled backfill」で、このロールの Codex 版が「Issue #94 のコメント上は実施スプリントが明示確定していません」と自らレビューコメントに記した上で、`current_phase` と一致する・1行置換のみ・件数が機械検算と合う、という機械検証可能性のみを根拠に `scheduled: "sprint-1"` への558件一括backfillを「このレビューでは許容範囲と判断しました」と自己判定してマージした。バックフィルの実施可否自体はオーナー承認済みだったが、**書き込む具体的な値の決定**は明示されておらず、レビューが値の妥当性を代わりに判定してしまった。）

## 同一欠陥をミラーごとに割らない理由（移設元：「出力（構造化）」の「同一欠陥をミラーごとに割らない」）

規範側「本リポジトリは `.claude/` ↔ `.codex/` ↔ `.agents/` の対称ミラーを持つため、1つの欠陥が
複数ファイルに同時に現れる」に続く根拠：

これを箇所ごとに別 finding に
すると、**同じ1件の欠陥が未解消件数を2倍3倍に水増しし**、`karte status` の「同一 finding が3ラウンド
連続未解消」というエスカレーション判定まで歪む。
再発番判定は summary の正規化文字列が完全一致すれば locus を問わず同一とし、
それ以外は locus が交差し、summary の類似度が閾値以上の場合に同一とする。

## finding ID を再利用する理由（移設元：「3. finding ID の再利用規定」）

規範側「未解消の指摘を再度挙げるときは、前回と同じ finding ID を再利用する」に続く根拠：

新しい ID を振り直すと
  「同じ指摘が何ラウンド残っているか」が数えられなくなり、`karte status` のエスカレーション判定
  （同一 finding が3ラウンド連続未解消）も類似アプローチの飽和判定も効かなくなる。

## allowlist の各項目がなぜその形なのか（移設元：「Bash 実行規律」節・Issue #373）

規範側には**本ロールが実際に打てるコマンド・フラグの一覧（＝レビューアの I/F）**だけを残し、
「なぜ deny なのか」という統制側の設計理由をここへ移した。

- **pytest が不可な理由**：任意 path/conftest/plugin を実行するため（第2次修正）。
- **`python3 -m karte` が deny な理由**（Issue #308）：カルテの書き手を `issue-fixer` に
  一本化するための非対称。
- **生 `git …` を deny して `gitgate` 経由にしている理由**：固定テンプレートを `shell=False` で
  組むため exec/write フラグが git に届かない。
- **`gh pr merge --admin` を許可フラグから外している理由**：第2次修正でブランチ保護バイパスを
  最小権限で塞ぐため。
- **`gh pr review --body-file` が allowlist 外である件**：over-deny 是正候補・要オーナー判断。
  このロールは `Write` を持たずどのみち `--body` を使うため実害はない。
- **`gh pr checkout` を allowlist から外した理由**（Issue #502 観測2・2026-09-09）：下記の節を参照。

## `feedback_ledger` を read-only に限定する理由（移設元：「Claude Code 固有の設定・権限境界」）

`feedback_ledger` はオーナー判断を扱う台帳（Issue #522）であり、本ロールに許可するのは read-only の
`check` / `status` / `index` だけである。台帳への記録、改訂案の起票、承認、棚卸しの確定に当たる
書き込み verb は許可しない。レビュー担当が書ける台帳は自分の finding を取り込む `karte ingest-reviewer`
だけで（下記「finding を handoff ファイル経由で本人が取り込む理由」）、オーナー判断を扱う記録装置は書き換えない。

## finding を handoff ファイル経由で本人が取り込む理由（Issue #375・2026-10-31 オーナー確定）

**問題**：構造化 finding の全文（9 項目 × 件数）が主文脈を 1 往復通過していた。さらに主文脈が取り込みレポートを
経由するため、`scope` 申告の原本が初出ラウンドから主文脈の手に触れ、改変の検出もできなかった（#523 のブロッカー）。
また Write も改行付き `--body` も使えず PR コメントを残せない事象があった（PR #479）。

**採用**：`pr-reviewer`（Claude Code）に `tmp/_handoff/pr-reviewer--*.md` への Write だけを PreToolUse フックで許し、
`karte ingest-reviewer` で本人が取り込む。ファイルなしで取り込む案は、ゲートが標準入力経由（パイプ・heredoc・改行）を
拒否するため成立しない。

**既存 `ingest-review` をそのまま解禁しなかった理由（却下案）**：`ingest-review` は `scope` と `disposition` 系を毎ラウンド
レポートの値で上書きする。そのまま渡すと (1) レビューアが自分で `waived` を書ける（オーナー専権の破れ）、(2) オーナーの決定が
毎ラウンド未決定へ戻る、(3) `--issue`/`--round` の取り違えで別 Issue の台帳へ書ける。このためレビューア専用 verb で
オーナー専権キーを拒否・保持し、issue/round はポインタ補完のみ、`--from` は handoff 名のみとした。オーナー決定の記録は
主文脈専用の `decide`、ポインタ初期化は `activate`。いずれもどのロールにも許可しない。

**#341 F-341-04 は維持**：`issue-fixer` の許可 verb は変えていない。取り込みの実行主体が「指摘した側」に移っただけで、
「指摘した側と直す側の分離」はむしろ強まる。

**Write 許可を `permissions.deny` でなくフックで行う理由**：Write 専用の deny エントリは効かない（Edit 規則が Write も
覆う・PR #688）。フックは realpath・symlink・`..`・ファイル名を検査し、検査不能は拒否する。

**残る限界**：`agent_type` の詐称と静的検査の限界は #129 と同じ。Codex 本体には Write と karte verb を許可しない。
Codex 経由の取り込みは下記の外側 wrapper 経路を使い、既存bindingを用意できない通常レビューの起動条件は未確認として扱う。
`gh pr comment --body-file` の許可は見送った（別途検討）。

**是正ラウンド 1（PR #697・F-375-02/03/05）の決定**：
- **共通 envelope（F-375-02）**：Issue #375 の追加 AC は #371 と同じ envelope で review artifact を識別することである。
  既存の `issue_envelope` は TOML 文書（IR/VD/CP/TD）の検査で、markdown の finding 本文には合わない。そこで
  束縛キーの語彙（producer・phase・issue・run_id・target_key・input_digest・snapshot_oid・artifact_type）だけを
  `karte/review_envelope.py` に写し（`issue_envelope.review_envelope` は再公開）、handoff 先頭ヘッダを共通項目つきに
  拡張した。写しの一致は単体テストで機械検査する。標準ライブラリだけで `karte` 内に置くのは、`karte` が単独配置
  （実プロセスの隔離コピーを使う既存テスト）でも動く設計だから。`issue_envelope` を直接 import する案は、その
  隔離コピーで `ModuleNotFoundError` になるため採らなかった。
  header が運ぶのは #371 の共通項目のうち schema/schema_version・producer・phase・issue・run_id・target_key・
  input_digest・snapshot_oid・artifact_type・status・next_expected_artifact。`verification`・`unresolved_findings`・
  `owner_decisions` は review では payload（finding 本文）と台帳が担うため header には持たない。
  却下案＝`artifact_type: ReviewReport` を `issue_envelope.schema` の SPECS へ足す（index・check・store が SPECS を
  走査するため、TOML 永続化を持たない review に副作用が及ぶ）。
- **期待値の置き場**：reviewer の自己申告から期待値を補うと束縛にならない。期待値は主文脈が `activate` でポインタへ
  記録する（Codex 経路はさらに binding 由来のヘッダ）。取り込み成功のポインタ更新で消えるので 1 回限りになり、
  取り込み済み handoff の再利用が構造的に拒否される。`artifact_type` は `ReviewReport`、`next_expected_artifact` は
  review が連鎖の終端なので常に空。phase は pr-reviewer の入力種別（TestDesign→`test_design`、ChangePlan→`implementation`）。
  却下案＝期待値を `ingest-reviewer` の CLI 引数にする（pr-reviewer が自分で与えられるので自己申告と同じ）。
- **round 1 の保護（F-375-03）**：保護モードの条件が「申告原本の存在」で、原本は最初の `ingest-reviewer` が作るため、
  それ以前の旧 `ingest-review` が無保護だった。期待値が残っている間は旧 `ingest-review` を拒否して round 1 でも迂回させない。
  当初案（`activate` が空の原本を先に作る）は F-375-10 で退けた：待機取消（期待値なしの `activate`）の後も原本が残り、
  退避経路の主文脈 `ingest-review` が追記専用の保護モードになって既存 finding の status を更新できなくなる。取消時に
  原本を消す案も退けた（ファイル削除という新しい書込み経路が要り、原本は追記専用が前提で、
  オーナー印（`decide --scope`）も同じファイルに残るので消すと守るべき値まで失うため。
  なお当初この理由を「0 件で取り込み済みの空の原本と区別できない」と書いたが、実経路では finding ブロックが 0 件の
  レポートは `model.parse_review` が原本の作成前に拒否するため、0 件取り込み済みの空の原本は存在しない・F-375-24）。
  採用＝`activate` はどちらの形でも原本を作らず、検証を通ったレビューア本人の取り込み（`ReviewerIngestPolicy.persist`）が
  原本を作る。作られるのは 1 件以上の申告があるときだけで、0 件の取り込みは拒否される（`persist` 直接呼びの
  単体テストだけが空の原本を作る・F-375-16。0 件の正式な扱いは別 Issue #801）。これで原本の有無は
  「レビューアが取り込み済みか／オーナー印があるか」と一致し（F-375-22 の窓だけは取り込み成功なしで原本が残りうる）、
  取消しても守るべきオーナー確定値だけが残る。原本のない scope をレビューア申告が置換したら取り込み結果に出す。
  残る限界＝主文脈が期待値なしで `activate` して旧 `ingest-review` を使う経路は、新規 finding の scope を主文脈が
  書ける（原本が無いのでその時点では検出できない）。後続のレビューア申告で食い違えば上記の置換として検出される。
  却下案＝旧 `ingest-review` を全面拒否（implementer/fixer の `out_of_scope_findings` の取り込みに使うため不可）。
- **原本→台帳の順序と書込失敗の窓（F-375-22）**：`persist` は台帳より先に原本を書く。逆順（台帳→原本）は、原本の
  書込みが失敗すると原本のない台帳だけが更新された無保護の round が残り、保護が欠けた状態で進むので採らなかった
  （保護側へ倒れる fail-close を優先）。代償は、原本の作成後に台帳の書込みが失敗（ENOSPC・EROFS・競合）すると、台帳に
  round が無いまま原本だけが残ること。拒否で終わりポインタも期待値も動かないため、同じ handoff の再実行で同じ round
  として回復でき、原本の同一記録は重複しない。再試行しなかった場合は、原本が追記専用で消えないので待機取消でも保護モード
  （新規 finding の追記専用）が残る。つまり「原本はレビューア取り込みの成功が作る」（F-375-10/16）は、この窓では
  取り込み成功なしに原本が残る例外を持つ。失敗時に原本を巻き戻す補償処理は入れなかった（原本は追記専用が前提で、
  補償は今回追記した行だけを消す新しい書込み経路になる。原本には過去ラウンドの申告とオーナー印が同居しうるので、
  ファイルごと消すことはできず、行単位の巻き戻しは誤って確定値を失うリスクを持ち込む）。
  窓は README「台帳の書込みが失敗した窓」にも書き、単体テストが固定する。
- **再掲漏れ（F-375-05）**：保護モードの「再掲漏れでも台帳を変更せず引き継ぐ」決定は維持し、書き込みは行ったうえで
  終了コード 5（`EXIT_INCOMPLETE`）で返す。対象を「レビューアが過去に申告した（原本がある）是正対象の未解消 finding」
  に絞るのは、主文脈が足した finding（fixer の `out_of_scope_findings` 等）とオーナーが申し送り／処置不要と決めた
  finding をレビューアが再掲しないのは正常だから（既存の単体テストが固定している挙動）。K-06 の拒否（何も書かない）へ戻す案は、
  取り込み済みの有効な finding まで失う・既存決定の変更になるため採らなかった。`karte status` への表示案は
  `karte/cli.py` が maintainability baseline の完全一致 fingerprint 対象で、変更に baseline 更新（オーナー確認）が要るため、
  本是正では終了コードを選んだ（`karte status` の表示が必要ならその baseline 更新とあわせて別途判断する）。

## Codex 出力を外側 wrapper で取り込む案B（Issue #375・オーナー承認）

Issue #375 の目的は「カルテ登録から主文脈の仲介をなくす」ことであり、Claude/Codex の違いで目的を変えない。
Claude の `pr-reviewer` は既存の `ingest-reviewer` を自分で実行できる。一方、Codex は read-only profileで
`karte` の書込も gate で拒否されるため、自分で取り込めない。

**採用した流れ**：Codex が `--role pr-reviewer` で正常終了した後、trusted な `codex_worktree_exec` wrapper が
`--output-last-message` の bytes を UTF-8 として読み、主 checkout の `tmp/_karte/active.json` と台帳の最新 round を
照合する。Issue は承認済み binding の `expected.issue` と起動時・取り込み直前のポインタを照合し、
round も起動時と取り込み直前で一致を要求する。ヘッダの Issue と次 round は起動時ポインタから決める。
wrapper は `karte/handoff_path.py` の許可名で handoff を作り、本文は加工せず、目印行が無ければ先頭に付けて、
既存 `ingest-reviewer` CLI を子プロセスで実行する。
Codex 本文に header がある場合は既存照合で一致を要求し、重複・不一致を拒否する。本文は解析・要約・書換えをせず、
別の LLM にも渡さない。呼び出し側には `取り込み済み: <path> (issue-N round R)` の1行と karte の警告行だけを返し、判定の要約は含めない。Codex 非ゼロ、空出力、pointer不在/不一致、
header・parse・保存・ID/round検査・取り込みの失敗は非ゼロで返し、runを完了扱いにしない。他ロールは従来動作のまま。

**信頼境界**：`.codex/config.toml` の read-only/network無効 profile、`agent-command-gate` の拒否表、
`pr-reviewer`×karte拒否を変更せず、Codexには台帳もhandoffも書かせない。外側 wrapper は既存の handoff 名検査、
pointer/header照合、`ingest-reviewer` の全検証を通すだけの受け渡し役で、owner判断を追加しない。

**起動条件**：既存の承認済み工程レビューでは、trusted caller が primary checkout から
`python3 -m issue_start.readonly_workspace --source <primary> --approval-file <approval> --role pr-reviewer -C <登録済みlinked worktree> ...`
を実行する。readonly入口が承認・artifact binding・入力を検査してから linked cwd で executor を起動するため、D5 の
`-C` と cwd toplevel の一致が保たれる。primary checkout から `codex_worktree_exec` を直接起動しない。
既存 wrapper は `pr-reviewer` 用の trusted artifact binding も必須とする。bindingのない一般 PR review に対する
起動手順は確認できておらず、信頼検査を緩めて補わない。

**却下案**：案A（Codexへ書込profileやkarte権限を足す）はread-only境界を破るので採らない。案C（Codex本文を
主文脈に返し、主文脈が解釈・整形して ingest-review する）は仲介を残し、転記時の意味変更・取りこぼしを作るため採らない。
案Bなら外側でファイル bytes を直接使い、trusted CLI の既存検証へ接続できる。

## `gh pr checkout` を「戻す契約」ではなく「切り替えない」で塞いだ根拠（Issue #502 観測2）

**事象**：`pr-reviewer` は `isolation` 指定なしで起動する（Claude 版）／`spawn_agent` に isolation 概念が
無い（Codex 版）ため、いずれも**呼び出し元と同じ作業ツリーの上で動く**。2026-09-08、PR #500 の是正
ラウンド2 で本ロールが `gh pr checkout` によりメインワークツリーを PR ブランチへ切り替え、`main` へ
戻さずに終了した（`git reflog` の `checkout: moving from main to claude/issue-493-…` が
`pr-reviewer` dispatch の実行中と一致）。以後の `issue-fixer` dispatch は
`gitgate adopt-branch` の stage 4（同名ローカル ref の存在検査）で 2回とも
`BRANCH_ADOPT_LOCAL_EXISTS` となり、主文脈が `git switch main` で復旧するまで是正に着手できなかった。

**選択肢**：

1. **契約に「切り替えたら戻す」と書く**（規範のみ）。
   - 利点：`gh pr checkout` が使えるままなので、ローカルでテストを走らせたいときの自由度が残る。
   - 欠点：**fail-open である**。戻し忘れ・レートリミットによる異常終了・セッション上限のいずれでも
     破れ、破れたときの症状（次 dispatch が必ず詰まる）は今回実際に起きた事象そのもの。加えて
     本ロールは `git`／`gitgate switch` を持たないため、**戻す手段が `gh pr checkout <既定ブランチ>` の
     ような迂回しかなく**、契約を守れる保証が構造として無い。
2. **`gh pr checkout` を allowlist から外す**（機械強制）。★採用
   - 利点：fail-close。切替能力そのものが無くなるので、戻し忘れ・異常終了という失敗経路が消える。
     レビューに checkout は不要で、差分は `rtk gh pr diff --no-compact` / `gh pr view` /
     `python3 -m gitgate diff|log` で読める（本ロールの契約は「読んだ差分・ファイル本文で確認する」
     であって「チェックアウトして動かす」ではない。`rtk gh pr diff --no-compact` の必須化の理由は
     本ファイル「Issue #530」節を参照）。
   - 欠点：レビューア自身がローカルでテストを実行して確認する経路が狭まる。ただし本ロールは
     `Write`/`Edit` を持たず、CI 結果は `gh pr checks` で読めるため、実害は小さいと判断した。
3. **切替を検知して自動で戻す仕組みを足す**。
   - 却下：新しい検知経路と復旧経路を1つずつ増やすことになり、Issue #502 のオーナー指摘
     （「検知経路を二重化しない」）に反する。壊れうる部品を増やして fail-open を延命する形。

**採用の根拠**：`.claude/rules/05-skills-agents.md` が定める push/merge の非対称は
「レビューアが共有状態を書き換えられない」ことを機械的に保証する設計であり、**ブランチ切替は
その非対称の穴だった**（push は塞がれているのに、作業ツリーの HEAD は動かせた）。穴は規範ではなく
ゲートで塞ぐ、という既存の方針（Issue #227 以降の allowlist 化）と揃う。

**現在の権限境界（Issue #542、2026-10）**：上記は Issue #502 当時の設計記録である。現在は Claude の native `permissions.deny` と Codex の execpolicy が直接形の merge command prefix を拒否し、両 PF の共有 `agent-command-gate` hook が global option、wrapper、API、検査可能な間接実行を全 AI ロールについて判定する。hook はロール別の push 等の境界も担う。移行の経緯と限界は [merge permission rationale](pr-merge-permission-settings.md) を参照。

**限界**：`.claude/hooks/agent-command-gate.sh` は静的なコマンド文字列検査であり sandbox ではない
（Issue #129）。本変更は「善意のエージェントが自然に踏む逸脱」を塞ぐもので、意図的な迂回までは
閉じない。

## `harm_detail` に処置方針が混入した経緯（PR #509・Issue #431 → Issue #511）

**事象**：PR #509（Issue #431）のレビューで、`harm_detail` に「依頼した Pyright 診断は本 PR の
差分範囲外の既存行における既存パターンで、新規追加テストによる新規発生ではない」「オーナー確認済み・
文書側を実装に合わせて訂正する方針で fix-here」といった**処置方針・判断経緯**が書かれたまま台帳へ
取り込まれ、オーナーの指摘で是正した（是正はラウンド4）。実害を書くべき欄が「なぜ直さなくてよいか」の
説明に置き換わると、`harm: real` の finding が読み手には実害なしに見え、処置方針の決定権が
レビュー担当へ滑る。

**原因は2つあり、Issue #511 でそれぞれを塞いだ**：

1. **規範側**：当時の「スコープ外の指摘も同じ finding として返す」節が、別 Issue にすべきと考える
   場合は「その旨を harm_detail と expected に書け」と指示しており、同じ節の「処置方針
   （disposition）は書かない」と自己矛盾していた。混入はレビュー担当の逸脱ではなく契約どおりの
   挙動だった。→ 契約を「harm_detail に書くのは実害だけ」「見立てはどの欄にも書かない
   （申告は `scope` まで）」に是正した。
2. **機械側**：取り込み（`python3 -m karte ingest-review`）に `harm_detail` の内容検査が無く、
   契約違反がそのまま台帳へ入った。→ `karte.model.check_harm_detail` を追加し、誤検出は
   `karte/allowlist.py` に理由付きで登録する運用にした。

**規範本文に1行しか残していない理由**：本ファイル冒頭の分担宣言のとおり、毎 dispatch で読む規範本文は
行動を決める記述に限り、経緯はここへ置く（Issue #511 のレビュー finding F-511-05）。

## 既知の限界（Issue #129で追跡・過信しない）（移設元：同名の節）

本エージェント自身によるPR #125レビューで、`.claude/hooks/agent-command-gate.sh` の正規表現ベースのpush拒否判定には迂回余地（コマンド置換・サブシェル・eval・別インタプリタ経由・改行区切り等）があることが判明済み。ハーネスのフックは唯一の防御ではなく多層防御の一枚。

## スコープ外指摘が finding 台帳を迂回した経緯（移設元：「スコープ外の指摘も同じ finding として返す」）

PR #490 では、スコープ外事項を構造化 finding の外に散文で列挙したため、指摘に `harm` が付かず記録台帳にも
取り込まれないまま clean 判定を通過して merge された。merge 後に実害ありと確定し、別 Issue として流出した。
選択肢は、スコープ外事項を参考情報として別枠に残すか、スコープ内外を `scope` 属性で表し同じ finding の列へ
入れるかであった。別枠は実害判定と clean 判定を再び迂回するため採らず、後者を採用した。したがって
`scope: out` は担当時期の申告にすぎず、`harm` の判定、台帳への記録、clean 判定の対象からは免除しない。

## squash の commit タイトル・本文を明示する理由（移設元：「レビュー契約」「Claude Code 固有の設定・権限境界」）

Issue #419 の対象は、GitHub 側の `squash_merge_commit_message` が `COMMIT_MESSAGES` の場合である。
この設定では複数 commit の subject/body が自動連結される。`--body` を省略して自動整形に委ねると、
`pr_merge_gate` は連結後の byte-level 形式を予測できず、`MERGE_MESSAGE_AMBIGUOUS` で拒否する。
これは `blocker_gate/closing.py` の意図的な fail-close であり、`--body` を明示すれば
`commit_message` が確定してこの分岐を回避できる。

## 手元テストを PR head の検証として扱わない理由（移設元：「レビュー契約」「Claude Code 固有の設定・権限境界」）

ブランチを切り替えない構成では、PR head の変更内容はレビューアの作業ツリーに存在せず、
`unittest` / `coverage` が検証するのは作業ツリーの指す base ブランチである（Issue #502 F-502-05）。
allowlist にテストランナーを残したのは、base 側の挙動確認や差分から立てた仮説の再現手順の確認に
使えるためである。PR のテスト成否を `gh pr checks` で確認する規則と、ローカル実行を許可する用途は
本文に残している。checkout 禁止の採用根拠は本ファイル「`gh pr checkout` を『戻す契約』ではなく
『切り替えない』で塞いだ根拠」に記録している。

## context-mode の index が持つ副作用（移設元：「Claude Code 固有の設定・権限境界」）

`ctx_index` による index 作成は外部 KB への永続副作用を持つ。本文には `ctx_search` / `ctx_index` を
調査に使うことと、`ctx_index` は非冪等なので同じ対象を重複 index しない規則を残した。

## `gh pr diff` に `--no-compact` を必須化し、`raw_tokens[:2] == ["rtk", "gh"]` を検証する理由（Issue #530）

大規模 PR で `pr-reviewer` が差分全文を取得できず、rtk（Bash 出力圧縮フック）の既定圧縮表示がファイル・
hunk を丸ごと省略しうることが実測で判明した（PR #554 自身の17ファイルの差分で、既定圧縮では
`tests/unit/test_gitgate.py` の差分が完全に非表示になった）。是正の過程で2つの案がオーナーにより
「rtk 迂回」として却下された経緯を記録する。

1. **1回目（PR #554・却下）**：`gitgate` に新規 verb `show-pr-diff` を追加し、内部で
   `subprocess.run(["gh","pr","diff",N])` を rtk を経由せず直接呼ぶ実装をした。rtk の設定・hook には
   一切触れていなかったが、「rtk が本来効くはずの出力に対して、rtk を一切経由しない別経路を新設した」
   こと自体が迂回と判定された。**技術的に rtk の設定を変えていないことは、迂回でないことの言い訳にならない**
   ——結果としてrtkの圧縮が及ばないデータ取得経路が新設されている時点で、機能的に迂回と同義である。
2. **2回目（一時的に却下→最終確定）**：`--no-compact` フラグの使用も一度は迂回扱いされたが、
   `rtk gh pr diff <N> --no-compact` が生の `gh pr diff <N>` とバイト完全一致することを実測した上で、
   最終的にオーナーは「`--no-compact` は rtk 自身が提供する正規の完全出力モードであり、これを
   pr-reviewer に**必須化**せよ」という方針に確定した（PR #557）。

この確定方針を実装した最初のバージョン（PR #557 初版）は、`--no-compact` の有無だけをゲートで検査し、
`rtk`/`command`/`exec`/`builtin` を一律「純ラッパー」として剥がしてから中身を検査する
`strip_wrappers_or_env_reason` の既存挙動に相乗りしていた。これは独立レビュー（別セッションの Codex）で
Critical 指摘（F-530-01）として発見された：ゲート自身は「`--no-compact` が付いているか」しか見ておらず
「実際に `rtk` を経由するか」を検証していない。シェルの `command`/`exec`/`builtin` は本来エイリアス・関数
解決を回避して直接実行するための組み込みコマンドであり、`command gh pr diff <N> --no-compact` のような
形で rtk の書き換えフック自体を回避できる懸念があった。是正として、pr-reviewer の `gh pr diff` に限り、
**2つの条件を両方**追加検証するチェックを両ゲート（`.claude/hooks/agent-command-gate.sh`・
`.codex/hooks/agent-command-gate.sh`）に入れた（PR #557 是正ラウンド・commit `5c61d06`）：
(1) `command_text.startswith("rtk ")`——生のコマンド文字列がリテラルの `rtk `（`rtk` に続く半角空白1つ）
で文字通り始まること。`rtk` の直後の空白が複数連続してもこの判定は通るが（`startswith` は先頭一致だけを
見るため）、`'rtk' gh ...` のように `rtk` を引用符で囲むと文字列としては `rtk ` で始まらなくなり、この
条件で deny される。
(2) トークン化後の `raw_tokens[:2] == ["rtk", "gh"]`——先頭トークンが `rtk`、次のトークンが `gh` である
こと。
二重ラップ（`rtk command gh pr diff ...`）は raw_tokens[:2] が `["rtk","command"]` になるため (2) で
確実に deny される。

## Claude Code と Codex CLI で差分取得の実装が異なる理由（Issue #530）

`--no-compact` 自体は両実行環境で共通だが、出力が大きすぎて呼び出し元ツール自身のインライン表示上限
（rtk とは無関係な、別の切り詰め要因）を超えたときの扱いが異なる。

- **Claude Code**：Bash ツール自身が、出力が閾値（実測で約30,000文字/107.5KB 程度）を超えると
  自動的に全文をファイルへ保存し「Output too large... Full output saved to: `<path>`」とパスを返す
  既存のハーネス機能を持つ。これは Issue #530 のために新規実装したものではなく、pr-reviewer は
  `rtk gh pr diff <N> --no-compact` を直接呼び、切り詰められたらそのファイルを `Read` するだけでよい。
- **Codex CLI**：`exec` ツールには同等の自動保存機構が存在しないことを実装時に確認した。そのため
  `gitgate` に薄いラッパー verb `show-pr-diff <N>` を追加し、内部で固定 argv
  `["rtk","gh","pr","diff",N,"--no-compact"]` を実行し、4,096 バイト（Claude Code の既定閾値・
  Codex CLI の既定 10,000 トークン予算のどちらに対しても保守的な安全マージンを見込んだ値）以下なら
  そのまま出力、超える場合は `tmp/pr-diffs/` へ保存してパス・バイト数・行数・SHA-256 を1行 JSON で返す。
  この verb は pr-reviewer ロール限定でゲートに許可されている（他ロールへは付与していない）。

保存ファイルの**作成時**の symlink 差し替え（TOCTOU）耐性は、`os.open(..., O_DIRECTORY | O_NOFOLLOW)` で得た
ディレクトリ fd を基準に `O_EXCL | O_NOFOLLOW` でファイル作成することで確保した（F-530-02・
独立レビューで発見・PR #557 是正ラウンドで対応）。

## `claude_review` MCP サーバーの rtk 迂回は対応しない（F-530-03・オーナー明示）

独立レビューで、`.codex/mcp/claude_review/server.py`（自弁の MCP サーバー実装）が rtk を経由せず
直接 `gh pr diff <N>` を呼んでおり、12万文字超の結果も切り捨てることが判明した（F-530-03）。
このサーバーは既に別件のインシデント対応
（`docs/methods/claude-review-remediation-plan.md`・F-01〜F-10）により
`~/.codex/config.toml` で `enabled = false` に無効化済みで、Step 1（封じ込め）完了・Step 2
（wrapper correctness PR）以降は未着手のまま保留されている。F-530-03 はこの既存の F-01〜F-10 のどれにも
該当しない新規発見だったが、**オーナー判断により対応しない**：Codex は Claude からサブエージェントとして
呼ぶ運用に統一しており、この MCP サーバーは再有効化しない。したがって同サーバーの是正計画
（Step 2 以降）自体も実施しない（2026-09-28 オーナー確定）。

## 差分全文を確認できなかった場合の自己申告を契約に残す理由（Issue #530 AC6・2026-09-29 オーナー確定）

Issue #530 の受入基準6は、全文を読めなかったときに `pr-reviewer` がそれを申告する契約の要否を
**判断として記録する**ことを求めていた。選択肢は次の2つだった。

1. **「プレビューだけで clean 判定しない」だけを規定する**（PR #557 の最終形）。
   欠点：禁止だけでは、読めなかった事実が記録に残らない。レビューアが黙って部分レビューを返すと、
   呼び出し元には「指摘なし」と区別がつかない。
2. **未確認の差分を `harm: real` / `severity: blocker` / `scope: in` の finding として自己申告し、
   判定を STOP にする** ★採用。finding は `karte ingest-review` で台帳へ取り込まれるため、実害あり finding のうち
   処置方針（`disposition`）が未決定のもの、または当該 PR で直す方針（`fix-here`）で未修正のものが残る間は
   `karte status` の verdict が clean にならない（機械ゲート）。未取得部分を推測で評価したり mergeable と判断したりしない。

経緯：この規定は PR #554（撤回）の初版にあったが、`--no-compact` 必須化へ設計を作り直した際に
PR #557 で落ちていた。Issue #530 の残件精査で AC6 が未達と判明し、オーナーが復活を決めた。
当初の `tests/unit/test_pr_reviewer_contract.py` は部分文字列検査と変異テストで文言の意味まで判定しようとしていた。しかし否定や同義表現を文字列パターンで網羅することはできず、指摘の向きが往復する状態が続いた。

**契約検査の方針（区分1、F-530-25）**：オーナーは、意味判定を装う部分文字列・変異検査から、空白だけ正規化した規定文との完全一致による変更検知へ単純化する案Aを採用した。契約の意味をテストで判定しようとせず、文言を意図して変えるときは期待文も更新する。これにより、否定・同義表現の解釈をテストに追加して指摘の向きが振り子のように反転する状態を終わらせる。同義の言い換えでも期待文の更新が必要になることは意図した設計である。

**保存差分の分割読取（区分1、F-530-27）**：Codex CLI で `rtk sed -n 401,600p <保存差分>` を実行した際、ツール側が切り詰め表示を出し、要求200行のうち184行しか返さなかった（original token count 6,643）。同じ範囲は raw `sed` と `rtk sed` で200行返ったため、原因は RTK ではなく Codex ツールの出力上限だった。約100行ずつ読み始め、切り詰め表示または返却不足があれば範囲を半分にして再確認する。1行でも切り詰められるか、保存後の短縮等で1行が空になる場合だけ未確認 finding で STOP し、全範囲の行数合計をマニフェストの `lines` と照合する。

既知の限界：レビューアが**切り詰めに実際に気づいたか**は機械では検証できず、自己申告に依存する。Codex 経路は `rtk sed -n <開始>,<終了>p <パス>` の返却に行番号が付かないため、返却データ行数と要求行数を確認する。Claude Code では `Read` の行番号で各範囲と最終データ行番号を照合する。いずれの経路も返却内容と SHA-256 の一致や、エージェントが最後まで読んだ事実を独立に監査する機構はない（多層防御の一枚であって、sandbox ではない。Issue #129 と同じ立場）。

**契約是正の経緯（区分1）**：以前の記述は、Codex でも Read の最終データ行番号をマニフェストと照合できるとしていた。この前提は Claude Code の `Read` には当てはまるが、`rtk sed -n` は行番号を出さず、要求範囲が EOF を越えても空出力で終了コード 0 になり得る。そこで Codex の契約を要求範囲ごとの実返却行数と、全範囲合計の照合へ改めた。

## Grep/Glob を外した根拠（Issue #535・2026-09-27）

本ロールは GATED_ROLES（issue-fixer/issue-implementer/pr-reviewer）の1つであり、frontmatter に
Grep/Glob を宣言しても実効的に配布されないことが実測で確認されている（本ロールは `isolation`
指定なし＝非 isolated で呼び出し元と同じワークツリー上で動くが、それでも同じ実効配布漏れが起きる）。
GATED_ROLES 共通の詳細根拠は複製を避けるため
[issue-fixer の rationale](issue-fixer.md)「ctx_search/ctx_index の付与根拠」に一本化した。

**本ロールへの ctx_search/ctx_index の付与自体は Issue #535 以前から既に行われている**（本ロールは
`.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」が定める検索系付与先の一般的な理由
（多数ファイルを読むロールに付与する）に元々含まれていた。「ノード横断検索が中核業務」は同節で
`dsv2-lookup` に固有の括弧書きであり、本ロールの付与理由ではない）。Issue #535 で本ロールに対して
変更したのは、実効配布が無いと確認された Grep/Glob を frontmatter から外したことと、
`.claude/agents/pr-reviewer.md` の context-mode 規律節に `ctx_index` の非冪等性への注意を追記した
こと（F-535-10 是正）の2点であり、ctx_search/ctx_index の新規付与は本 Issue では
issue-fixer/issue-implementer の2ロールに限られる。

## Codex で保存差分を読めるようにするゲート例外（F-530-13）

Codex の `gitgate show-pr-diff` は大きな差分を `tmp/pr-diffs/` に保存するが、既存ゲートは `sed` を
拒否し、Serena も gitignore 対象の `tmp/` を読めなかった。保存ファイル全文を確認する経路が無いことが判明した。

1. **Serena の設定を変更する**（不採用）：`.serena/` は gitignore 対象でリポジトリに載らず、設定の
   ずれや欠落が追跡されないまま機密の取りこぼしを静かに起こし得る。
2. **Codex ゲートに限定許可を足す**（案B・採用）：`pr-reviewer` だけに `rtk sed -n <開始>,<終了>p <パス>`
   を許可し、既存の wrapper strip 後に引数列・行範囲・実ファイルを検査する。

許可条件は、`tmp/pr-diffs/` 配下で `pr-<PR番号>-<32桁hex>.diff` 形式の名前に一致する通常ファイルであることと、`rtk sed -n <開始>,<終了>p <パス>` の形であることだ。ゲートはファイルが `show-pr-diff` によって生成されたかを確認しないため、同形式の任意の通常ファイルも読める。

残余リスク（F-530-23、オーナー判断待ち）：同形式の任意ファイルを読めることに加え、ゲートが no-follow で通常ファイルと確認した後に fd を閉じ、後続の `rtk sed` が開く前にパスを symlink へ差し替えられる TOCTOU の窓がある（F-530-22）。許容の判断はオーナー判断待ちである。

フックが未信頼でゲートが動作していなかった経緯は F-530-21 で別扱いとし、本 finding の是正範囲には含めない。

## 保護モードでの二経路の併用（PR #697 見直し）

初期案は `ingest-reviewer` を使った Issue の `ingest-review` を拒否し、専権キーも取り込みごと
拒否した。しかし実装・是正担当の `out_of_scope_findings` は主文脈の `ingest-review` で取り込む
契約のため、その経路を塞いでいた。さらに K-06 の再掲必須は範囲外指摘だけの追加を拒んだ。

オーナーは完全な入力を一度で要求しない方針を承認した。申告原本がある Issue の両経路を
保護モードとし、finding ブロック内の専権キーは空値も無視して警告する。前書きの専権キーは
構文エラーとして拒否する。値を保存しないためオーナー決定を守り、未決の finding は verdict ゲートに
残る。再掲されなかった open finding は警告して未解消のまま引き継ぐ。不在を解消と扱わず、解消には
明示の `status: resolved` を要求するため、保護モードだけで K-06 の拒否を緩めても未解消を隠さない。
入力先を誤らせるパス・ヘッダや解釈不能な書式は引き続き拒否する。

経路ごとの更新権限は異なる。レビューア本人の `ingest-reviewer` は既存 finding を再掲して
`scope` / `status` を更新できる。`--round` に台帳の最新 round を明示すると同じ round の取り込みを許可するが、
`### new` で台帳の未解消 finding と同一の指摘を再発番すると拒否され、既存 ID の再掲だけなら成功しうる。
同じ round の再取り込みは台帳の状態遷移を壊しうるため、ポインタ書込み失敗の回復には使わない。
主文脈が `karte render --issue <N>` で当該 round の記録を確認し、`activate` でポインタを向け直す
（`karte/README.md`「進行ポインタの書込みが台帳より後に失敗した窓」）。
主文脈の保護 `ingest-review` は実装・是正担当からの範囲外指摘など新規 finding の追記専用とし、
既存 ID の再掲が1件でもあれば全件拒否して何も書かない。既存指摘の変更は `decide` または
レビューア本人の取り込み経路に委ねる。未再掲の open finding は従来どおり引き継ぐ。

新 verb は採らず、既存の主文脈専用 `ingest-review` に保護を適用する。許可表を拡げずに既存の
運用手順を復旧できるためである。範囲外指摘の追記では最新 round を明示し、レビュー round を
消費しない。ポインタが遅れて省略 round が台帳の最新値と一致すれば、主文脈経路はその同じ round に
追記する。申告原本はレビューアの申告に限り、主文脈の追加を混ぜない。オーナー scope 印を原本へ
保存した後の台帳書込みが失敗しても、次の保護取り込みは印の値を台帳へ再適用する。
Codex の `pr-reviewer` gate には karte verb が許可されない。Codex 経路では外側 wrapper が
`ingest-reviewer` を実行し、権限表は広げない（案Bの詳細は前述）。
申告原本がない従来経路は従来どおり毎ラウンド上書き・再掲必須を維持する。
