"""類似アプローチの機械判定と、飽和時のアプローチ転換指令の生成。

**回数ではなく類似で切る**。ラウンド上限は設けないので、毎回違う角度で攻めている限り
``append`` は何度でも通る。止めるのは「同じアプローチの無駄連打」だけ。

判定は決定論的な **2 つの独立信号の OR**:

宣言信号
    ``root_cause`` が同じ **かつ**（``change_kind`` が同じ **or** ``targets`` が交差する）。
    交差の相手は過去 Attempt の **実効 targets ＝宣言 targets ∪ 実測 touched** を使う
    （宣言だけを見ると「実際には同じ場所を触っていた」試行を取りこぼすため）。

実測信号
    実際の差分から算出した touched-set が前の試行と一致する。ラベル（``root_cause`` /
    ``change_kind``）を付け替えてゲートをすり抜けるのを防ぐため、宣言だけに依存しない。
    **少なくとも片側に実測値があるときだけ**発火させる（宣言 targets 同士の一致は
    宣言信号の領分であり、実測信号を名乗らせない）。

タイミングの扱い（Issue #307「実装上の補足」への回答＝採用方式）:
    診断（``append``）は修正の**前**に走るため、新規 Attempt には実測値が存在しない。
    そこで新規 Attempt の scope には宣言 ``targets`` を使い、比較相手である過去 Attempt 側に
    ``close-attempt`` で取り込んだ実測 ``touched`` を使う。ラベルを変えても実際に同じ場所を
    触っていた試行は、**次のラウンドの判定で**この実測信号に捕捉される。

発火条件:
    新規 Attempt が対象とする **未解消 finding** を共有する過去 Attempt のうち、
    上記いずれかの信号で類似と判定されたものが **2 件に達したら 3 件目を許さない**。

判定は 1 つしか持たない（K-09）:
    ``append`` のゲートも ``render`` / ``status`` の表示も :func:`find_hits` ＋
    :func:`is_saturated` の **pairwise 件数**だけで決める。以前は表示側だけが union-find の
    連結成分（``cluster``）を使っており、推移律で広がるクラスタとゲートの pairwise 件数が
    食い違って「``render`` が飽和と言った直後に ``append`` が成功する」状態が起きた
    ——後工程が表示を「次の ``append`` が落ちる」と誤読する。表示側は「既に書かれた
    Attempt k の宣言をそのまま繰り返す仮想の新規試行」を主語に置くことで、同じ関数で
    同じ意味（＝その再試行は拒否される）を出せる（``karte.cli._saturated_groups``）。
    **2 つ目の類似判定を足さないこと**——足した瞬間に同じ食い違いが再発する。

依存仕様: :mod:`karte` の docstring（Issue #307「類似判定（決定論・2つの独立信号の OR）」）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

SATURATION_THRESHOLD = 2  # 類似グループがこの数に達したら次（3件目）を拒否する


def entry_file(entry: str) -> str:
    """``path::symbol`` のファイル部分。``::`` が無ければそのもの。"""
    return str(entry).split("::", 1)[0].strip()


def has_symbol(entry: str) -> bool:
    return "::" in str(entry)


def scope_signature(entries) -> frozenset:
    """set 比較用の署名。``file::symbol`` はファイル単位の要素も併せ持つ。

    ``git diff`` から算出する touched-set は「変更ファイル＋変更シンボル」の両方を含むため、
    宣言 ``targets``（関数/クラス単位）側もファイル要素へ展開して同じ土俵に載せる。
    """
    signature = set()
    for entry in entries:
        text = str(entry).strip()
        if not text:
            continue
        signature.add(text)
        if has_symbol(text):
            signature.add(entry_file(text))
    return frozenset(signature)


def overlapping_entries(left, right) -> list:
    """``targets`` の交差要素（左辺の表記で返す・表示用に決定論ソート）。

    完全一致に加え、「片方がファイル指定・もう片方がそのファイル内のシンボル指定」も
    交差とみなす（粒度差で取りこぼさないため）。別シンボル同士は交差としない。
    """
    hits = set()
    for x in left:
        for y in right:
            xs, ys = str(x).strip(), str(y).strip()
            if not xs or not ys:
                continue
            if xs == ys:
                hits.add(xs)
            elif entry_file(xs) == entry_file(ys) and not (has_symbol(xs) and has_symbol(ys)):
                hits.add(xs)
    return sorted(hits)


@dataclass(frozen=True)
class AttemptView:
    """類似判定に必要な最小の投影（カルテのモデルから組み立てる）。"""

    number: int
    root_cause: str
    change_kind: str
    targets: tuple = ()
    touched: tuple = ()

    @property
    def effective_targets(self) -> tuple:
        merged = list(self.targets)
        for entry in self.touched:
            if entry not in merged:
                merged.append(entry)
        return tuple(merged)

    @property
    def scope(self) -> tuple:
        """類似の比較対象。実測があれば実測、無ければ宣言 targets。"""
        return self.touched if self.touched else self.targets


@dataclass(frozen=True)
class SimilarityHit:
    """過去 1 件との類似判定の結果（どの信号で・何が反復したか）。"""

    prior: int
    declared: bool
    measured: bool
    root_cause: str = ""
    same_change_kind: str = ""
    overlapping_targets: tuple = ()
    measured_scope: tuple = ()

    @property
    def signals(self) -> list:
        names = []
        if self.declared:
            names.append("宣言信号")
        if self.measured:
            names.append("実測信号")
        return names


def compare(new: AttemptView, prior: AttemptView) -> SimilarityHit | None:
    """``new`` が ``prior`` と類似かを判定する。非類似なら ``None``。"""
    overlaps = overlapping_entries(new.targets, prior.effective_targets)
    same_root_cause = bool(new.root_cause) and new.root_cause == prior.root_cause
    same_change_kind = new.change_kind == prior.change_kind
    declared = same_root_cause and (same_change_kind or bool(overlaps))

    prior_scope = scope_signature(prior.scope)
    new_scope = scope_signature(new.scope)
    has_measurement = bool(prior.touched) or bool(new.touched)
    measured = bool(has_measurement and prior_scope and new_scope and prior_scope == new_scope)

    if not (declared or measured):
        return None
    return SimilarityHit(
        prior=prior.number,
        declared=declared,
        measured=measured,
        root_cause=new.root_cause if same_root_cause else "",
        same_change_kind=new.change_kind if (declared and same_change_kind) else "",
        overlapping_targets=tuple(overlaps),
        measured_scope=tuple(sorted(prior_scope)) if measured else (),
    )


def find_hits(new: AttemptView, priors) -> list:
    """``priors`` のうち ``new`` と類似する試行を古い順に返す。"""
    hits = []
    for prior in sorted(priors, key=lambda item: item.number):
        hit = compare(new, prior)
        if hit is not None:
            hits.append(hit)
    return hits


def is_saturated(hits) -> bool:
    return len(hits) >= SATURATION_THRESHOLD


@dataclass
class Directive:
    """アプローチ転換指令（``append`` 拒否時・``render`` 表示時に出す本文）。"""

    lines: list = field(default_factory=list)

    def text(self) -> str:
        return "\n".join(self.lines)


PIVOT_AXES = (
    "change_kind を変える（logic で駄目なら data-structure / interface / config を疑う）",
    "レイヤを変える（呼び出し元・入力データ・境界の契約・テスト側の前提を疑う）",
    "最小再現に切り分ける（revert して失敗する最小ケースを作り、仮説を1つずつ潰す）",
    "指摘の読み直し（finding の harm_detail を再読し、症状ではなく被害から逆算する）",
)


def build_directive(
    new: AttemptView, hits, open_finding_ids, *, subject_label: str = "今回の宣言"
) -> Directive:
    """反復された ``root_cause`` / ``targets`` を**名指しした**転換指令を組み立てる。

    ``subject_label``
        ``new`` が何を指すかの見出し。``append`` の拒否時は実際に書き込もうとした宣言
        （既定「今回の宣言」）、``render`` / ``close-attempt`` の表示時は既存 Attempt の
        宣言をそのまま繰り返す仮想の再試行（「飽和したアプローチ」）を指す。同じ文面で
        主語だけが違うため、読み手が取り違えないようラベルを明示させる（K-09）。
    """
    repeated_root_causes = sorted({hit.root_cause for hit in hits if hit.root_cause})
    repeated_targets = sorted({entry for hit in hits for entry in hit.overlapping_targets})
    measured_priors = sorted(hit.prior for hit in hits if hit.measured)
    declared_priors = sorted(hit.prior for hit in hits if hit.declared)
    measured_scope = sorted({entry for hit in hits for entry in hit.measured_scope})

    lines = [
        "DIRECTIVE: アプローチ転換（類似グループ飽和のため 3 件目の同種 Attempt は書き込まない）",
        f"  対象の未解消 finding: {', '.join(sorted(open_finding_ids)) or '(なし)'}",
        f"  類似と判定した過去 Attempt: {', '.join(str(hit.prior) for hit in hits)}",
    ]
    if repeated_root_causes:
        lines.append(
            f"  反復された root_cause: {', '.join(repeated_root_causes)}"
            f"（宣言信号・Attempt {', '.join(str(n) for n in declared_priors)}）"
        )
    if repeated_targets:
        lines.append(f"  反復された targets: {', '.join(repeated_targets)}")
    if measured_priors:
        lines.append(
            f"  実測 touched-set が一致した Attempt: {', '.join(str(n) for n in measured_priors)}"
            "（ラベルを変えても実際に触った場所が同じ）"
        )
        if measured_scope:
            lines.append(f"  一致した touched-set: {', '.join(measured_scope)}")
    lines.append(
        f"  {subject_label}: root_cause={new.root_cause} / change_kind={new.change_kind} / "
        f"targets={', '.join(new.targets)}"
    )
    lines.append("  指令: 上記の root_cause 仮説と targets を**再び対象にしない**別アプローチを立てること。")
    lines.append("  転換軸の候補:")
    for axis in PIVOT_AXES:
        lines.append(f"    - {axis}")
    return Directive(lines)
