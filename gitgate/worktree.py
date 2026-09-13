"""worktree の回収・解放 verb（Issue #354・PR-2／Issue #502）。

本モジュールが実装する4 verb:

``worktree-release``
    linked worktree を**冪等に**解放（削除）する（FR-W5）。台帳の状態が「解放してよい」と
    言っているときだけ削除する。``running``（live な dispatch が所有）と ``stopped``
    （停止済みだが未回収）は ``--force-*`` でも上書きできない。
    **実体の削除経路はここだけ**——``abandoned``（``worktree-forget`` 済み）で実体が残って
    いる場合も、台帳を進めずに実体だけ削除する（F-354-02）。
    **worktree 実体の削除に成功し、かつ ``cleanup_branch_ref=True``（既定）のときは、台帳の
    ``branch_name`` に対応するローカルブランチ ref の削除を試みる**（``git branch -D``・
    Issue #426。F-426-01 で安全化）。``cleanup_branch_ref=False`` を渡す呼び出し元
    （``issue-start-gate`` の毎 dispatch 経路・Issue #464 F-464-06）ではこの削除を丸ごと
    スキップする——``git fetch`` を伴うため、毎 dispatch のホットパスにネットワーク I/O を
    持ち込まない。フル掃除は ``SessionStart`` フックが別途 ``cleanup_branch_ref=True`` で
    行う。放置すると、
    その ref が ``gitgate adopt-branch`` の stage 4（同名ローカル ref の存在検査）に
    引っかかり、次の ``issue-fixer`` の adopt が ``BRANCH_ADOPT_LOCAL_EXISTS`` で失敗する。
    ただし ``git branch -D`` は force delete でありローカルにしか無いコミットを reflog ごと
    黙って破棄しうるため、削除の前に fresh fetch した ``refs/remotes/origin/<branch>`` に
    対してローカル ref の tip が祖先であることを確認し、確認できない場合は削除せずスキップ
    する（:func:`_cleanup_branch_ref`）。この判定は**フェイルオープン**——削除・スキップの
    どちらの結果でも worktree 実体の削除という主契約は成立済みなので ``worktree_release()``
    全体を失敗させない。成否・スキップ理由は必ず ``_note()`` で台帳に記録する。他 worktree
    が checked out 中のブランチを誤って消さない安全網は ``git branch -D`` 自身の拒否に委ねる
    （``git worktree remove`` の成功が保証するのは「この worktree がもう branch_name を
    掴んでいない」ことだけで、別の worktree の不在までは含意しない）。削除されずに stray ref
    が残った場合の安全網は ``adopt_branch()`` 側の tip 一致検査（``BRANCH_ADOPT_LOCAL_EXISTS``
    への fail-close、無害なら reclaim。詳細は ``gitgate/adopt.py`` のモジュール docstring）。

``collect-worktree``
    **回収 → 検証 → 解放を1操作に畳む**（候補D・FR-W2）。段構造で、前段が失敗したら後段を
    実行しない——特に「handoff を回収できていないのに worktree を消す」ことが起こらない。
    これは検査で守るのではなく、呼び出し順序そのもので守る。
    **回収は済んだが最後の ``git worktree remove`` が worktree ロックで失敗した場合**
    （停止途中のエージェントがまだ掴んでいる・Issue #464）は、成果物が ``collected_to`` へ
    退避済みで失われていないので例外を投げず、台帳を ``release_pending`` にして削除だけを
    ``issue-start-gate`` の次回実行へ遅らせる（``ISSUE_START_WORKTREE_RESIDUE`` で次
    dispatch を止めない）。

``worktree-forget``
    回収不能な ``stale`` エントリを ``abandoned`` へ逃がす。**worktree は消さない**
    （消すのは ``worktree-release``。責務を混ぜない。``abandoned`` にした後で
    ``worktree-release <path>`` を呼べば、台帳を ``released`` へ進めずに実体だけ消える）。
    **エントリも消さない**——
    `.claude/rules/01-principles.md`「PR8「消さない」の適用範囲」区分1（決定履歴の保全）に
    従い、``reason`` 付きで状態遷移だけを記録する。

``worktree-sweep-abandoned``
    **異常終了（レートリミット／セッション上限による強制停止）で ``running`` のまま取り残された
    エントリを回収・解放する**（Issue #502・観測1）。``SubagentStop`` フックが発火しない終了経路
    では台帳が ``running`` に留まり、worktree も対象ブランチを掴んだまま残るため、次の
    ``adopt-branch`` が ``BRANCH_ADOPT_LOCAL_EXISTS`` で必ず失敗して是正ループが止まる。

    **``running`` は「入れ子委譲待ちの正当な保留」でもある**（Issue #423）ため、状態だけでは
    異常終了と区別できない。区別に使うのは**呼び出し地点そのもの**である——
    :func:`sweep_abandoned_running` は「live な dispatch が1つも無いことを呼び出し元が観測した」
    という申告（``no_live_dispatch=True`` ／ CLI では ``--no-live-dispatch``）が無ければ**何も
    しない**。この申告を出せる地点は現状ひとつだけで、``.claude/hooks/resume-watcher.sh`` が
    レートリミット解除を確認し、かつ対象ペインが**アイドル**（``pane_guard`` が WORKING を
    返さない）と観測した復帰イベントである。オーナー指示
    （2026-09-08）どおり**復帰の契機は既存のレートリミット復帰イベントに相乗りし、検知経路を
    二重化しない**。

    **この申告の観測範囲は watcher に渡された単一 tmux ペインに限られる**（F-502-02）。
    ``pane_guard`` は引数で渡された ``$PANE`` しか見ないのに対し、台帳はリポジトリ全体で
    共有される。したがって別ペイン・別セッションで live な dispatch が動いていても
    ``no_live_dispatch`` は真になりうる——この申告は「**そのペインからは**サブエージェントが
    実行中でない」以上のことを主張しない。

    **クロスペインの保護を担うのは git の ``locked`` だけである**：
    ``git worktree list --porcelain`` が ``locked`` を報告する worktree を掃引対象から外す
    （ハーネスが live な agent worktree をロックする構成であれば、これが #423 の入れ子委譲中
    エントリを別ペインからも守る）。**ハーネスがロックしない構成ではこの保護は成立しない**ので、
    その環境では掃引そのものを止める（``CLAUDE_RL_SWEEP_WORKTREES=0``）。

    **成果物を失わない側に倒す**: 自分の handoff が1件あれば ``collect-worktree`` と同じ段
    （回収 → sha 検証）を通し、**その上で作業ツリーが clean であることを確認できたときだけ**
    解放する。handoff が無い場合は「捨ててよいと**積極的に確認**できた」ときだけ解放する
    （作業ツリーが clean かつ HEAD が ``origin/<branch>`` に含まれる）。確認
    できなければ解放せず ``stale`` へ落とし、既存の ``ISSUE_START_WORKTREE_RESIDUE`` deny
    （解消コマンド付き）へ合流させる。**clean 検査を handoff の有無で免除しない**
    （F-502-01）——実体の削除は ``git worktree remove --force`` であり、dirty/untracked を
    問答無用で消す。handoff が書けていることは「作業ツリーに未コミットの何かが残っていない」
    ことを含意しない。

本 PR のスコープ（重要）
----------------------
ここで実装するのは**実体だけ**で、gated ロール（``issue-implementer`` / ``issue-fixer`` /
``pr-reviewer``）への権限付与は行わない。``agent-command-gate.sh`` の
``GITGATE_VERBS_BY_ROLE`` は allowlist であり、**未登録の verb は既定 deny** される。
したがって実装が先行しても gated ロールの権限は1ミリも増えない（登録は PR-3/PR-4）。

削除経路を持つがゆえのガード
--------------------------
本モジュールは PR-1（``issue_start/worktree_ledger.py``）と違い**削除経路を持つ**ため、
「何を消してよいか」を構造で絞る。:func:`validate_worktree_path` を通過するのは
``.claude/worktrees/agent-<id>`` ちょうどの形だけで、絶対パス・``..``・サブディレクトリ・
symlink 構成要素・repo-root 外へ解決されるパスはすべて git を呼ぶ前に拒否する。
さらに ``git worktree list --porcelain`` に linked worktree として現れないパスは消さない
（git 管理外のディレクトリを ``git worktree remove`` の名の下に消さない）。

時刻の扱い（`.claude/rules/04-test-data.md` 遵守）
------------------------------------------------
``now`` は**必ず引数で注入する**。本モジュールは ``datetime.now()`` / ``time.time()`` を
一切呼ばない（wall clock を読むのは CLI 境界＝``gitgate/cli.py`` だけ）。TTL・経過時間による
判定も設けない——判定は状態（台帳の ``status``）と実在の突き合わせだけで行う。

依存仕様:
  * ``issue_start/worktree_ledger.py``（PR-1・状態遷移と台帳 I/O。``WORKTREE_PATH_RE`` /
    ``ENTRY_ID_RE`` は再定義せず import 再利用する）
  * ``.claude/agents/issue-implementer.md`` / ``issue-fixer.md`` の「``handoff_path`` の検査」
    （6条件。:func:`validate_handoff_relpath` が同一の規則を機械化したもの）
  ※ いずれも out-of-graph（版なし）。本モジュールは
    `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**区分（Issue 運用パイプライン）に属する。
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from issue_start.worktree_ledger import (
    DEFERRED_RELEASE_STATUS,
    ENTRY_ID_RE,
    WORKTREE_PATH_RE,
    LedgerError,
    add_note,
    main_worktree_root,
    mark,
    read_ledger,
)

# `git fetch` 用のタイムアウト（秒）。到達不能/認証待ちで無期限にハングしないよう、CI/自動化
# 文脈での妥当な既定値として 30 秒を採る（Issue #426・F-426-05）。
FETCH_TIMEOUT_SECONDS = 30

# 回収する handoff の上限。想定は数 KB の YAML であり、これを超えるものは「handoff ではない何か」
# （ログの取り違え・生成物の混入）なので回収せず止める。
DEFAULT_MAX_HANDOFF_BYTES = 1_048_576

HANDOFF_DIR_PARTS = ("tmp", "_handoff")
COLLECTED_DIRNAME = "collected"

# handoff ファイル名の規則（`.claude/agents/issue-implementer.md`「入力」節の 4・5 と同一）。
#   <agent>--issue-<N>[<境界><suffix>].yaml
# `issue-<N>` の**直後の1文字が `-` か `.`** であることを要求する。この境界検査が無いと
# `issue: 354` の呼び出しで `…--issue-3541.yaml`（別 Issue のファイル）を受理してしまう。
HANDOFF_FILENAME_RE = re.compile(
    r"^(?P<agent>[A-Za-z0-9][A-Za-z0-9._-]*)--issue-(?P<issue>[0-9]+)"
    r"(?P<suffix>-[A-Za-z0-9._-]*)?\.yaml$"
)
_SAFE_PATH_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_REASON_LEN = 1000


class WorktreeError(Exception):
    """worktree を一意に特定できない/解放してよいと言えない場合の fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


# --- 引数スキーマ --------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseRequest:
    worktree_path: str
    entry_id: str | None = None
    force_uncollected: bool = False
    reason: str = ""


@dataclass(frozen=True)
class CollectRequest:
    entry_id: str | None = None
    worktree_path: str | None = None
    handoff_path: str | None = None
    into: str | None = None
    allow_missing_handoff: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ForgetRequest:
    entry_id: str
    reason: str


@dataclass(frozen=True)
class SweepRequest:
    """``worktree-sweep-abandoned`` の引数（Issue #502）。

    ``no_live_dispatch`` は「live な dispatch が1つも無いことを呼び出し元が観測した」という
    **申告**であり、これが無ければ掃引は何もしない（#423 の入れ子委譲中 ``running`` を
    誤って解放しないための構造的な条件）。
    """

    reason: str
    no_live_dispatch: bool = False


@dataclass(frozen=True)
class SweepEntryOutcome:
    entry_id: str
    worktree_path: str
    action: str
    detail: str = ""


@dataclass(frozen=True)
class ReleaseOutcome:
    worktree_path: str
    entry_id: str | None
    removed: bool
    status: str


@dataclass(frozen=True)
class CollectOutcome:
    worktree_path: str
    entry_id: str | None
    collected_to: str | None
    released: bool


def _reject_control_chars(value: str, what: str) -> None:
    if "\n" in value or "\r" in value or "\0" in value:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", f"{what} contains control characters")


def _validate_entry_id(value: str) -> str:
    if not isinstance(value, str) or not ENTRY_ID_RE.fullmatch(value):
        raise WorktreeError("WORKTREE_ENTRY_ID_INVALID", repr(value))
    return value


def _validate_reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorktreeError("WORKTREE_REASON_EMPTY")
    _reject_control_chars(value, "reason")
    if len(value) > _MAX_REASON_LEN:
        raise WorktreeError("WORKTREE_REASON_TOO_LONG", str(len(value)))
    return value


def _parse_flags(
    args: Sequence[str],
    *,
    value_flags: set,
    bool_flags: set,
    allow_positional: bool,
) -> tuple:
    """固定 schema の flag parse。未知/重複 flag・値欠落は拒否する（副作用なし）。"""
    positional: str | None = None
    index = 0
    if allow_positional and args and not args[0].startswith("-"):
        positional = args[0]
        index = 1
    values: dict[str, str] = {}
    flags: set = set()
    while index < len(args):
        token = args[index]
        if token in bool_flags:
            if token in flags:
                raise WorktreeError("WORKTREE_ARGUMENT_INVALID", f"duplicate {token}")
            flags.add(token)
            index += 1
            continue
        if token in value_flags:
            if token in values or index + 1 >= len(args):
                raise WorktreeError("WORKTREE_ARGUMENT_INVALID", token)
            values[token] = args[index + 1]
            index += 2
            continue
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", token)
    return positional, values, flags


def parse_worktree_release_args(args: Sequence[str]) -> ReleaseRequest:
    positional, values, flags = _parse_flags(
        args,
        value_flags={"--entry", "--reason"},
        bool_flags={"--force-uncollected"},
        allow_positional=True,
    )
    if positional is None:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing <worktree-path>")
    force = "--force-uncollected" in flags
    reason = values.get("--reason", "")
    # `--force-uncollected` があれば必須、単独で渡されたときも検証する（受理した理由は
    # 必ず台帳へ載るので、制御文字・過長のものをここで落とす＝F-354-04）。
    if force or reason:
        _validate_reason(reason)
    return ReleaseRequest(
        worktree_path=validate_worktree_path(positional),
        entry_id=_validate_entry_id(values["--entry"]) if "--entry" in values else None,
        force_uncollected=force,
        reason=reason,
    )


def parse_collect_worktree_args(args: Sequence[str]) -> CollectRequest:
    positional, values, flags = _parse_flags(
        args,
        value_flags={"--entry", "--handoff", "--into", "--reason"},
        bool_flags={"--allow-missing-handoff"},
        allow_positional=True,
    )
    entry_id = _validate_entry_id(values["--entry"]) if "--entry" in values else None
    if positional is None and entry_id is None:
        raise WorktreeError(
            "WORKTREE_ARGUMENT_INVALID", "either <worktree-path> or --entry is required"
        )
    allow_missing = "--allow-missing-handoff" in flags
    reason = values.get("--reason", "")
    if allow_missing or reason:
        _validate_reason(reason)
    if positional is not None and entry_id is None and "--handoff" not in values:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing --handoff")
    return CollectRequest(
        entry_id=entry_id,
        worktree_path=validate_worktree_path(positional) if positional is not None else None,
        handoff_path=values.get("--handoff"),
        into=values.get("--into"),
        allow_missing_handoff=allow_missing,
        reason=reason,
    )


def parse_worktree_forget_args(args: Sequence[str]) -> ForgetRequest:
    _positional, values, _flags = _parse_flags(
        args,
        value_flags={"--entry", "--reason"},
        bool_flags=set(),
        allow_positional=False,
    )
    if "--entry" not in values:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing --entry")
    if "--reason" not in values:
        # 理由なしの ``abandoned`` は「なぜ諦めたか」を失う＝後から再構成できない一次情報の
        # 取りこぼしになる（PR8 区分1）。必須にして構造的に防ぐ。
        raise WorktreeError("WORKTREE_FORGET_REASON_REQUIRED")
    return ForgetRequest(
        entry_id=_validate_entry_id(values["--entry"]),
        reason=_validate_reason(values["--reason"]),
    )


def parse_worktree_sweep_args(args: Sequence[str]) -> SweepRequest:
    """``worktree-sweep-abandoned --no-live-dispatch --reason <text>`` を parse する。

    どちらのフラグも**必須**にする。``--reason`` は台帳へ残す一次情報（なぜ掃引したか）で、
    ``--no-live-dispatch`` は「live な dispatch が1つも無いことを観測した」という申告
    （Issue #423 の保留 ``running`` を誤解放しないための前提）。欠けたら git も台帳も一切
    触らずに fail-close する。
    """
    _positional, values, flags = _parse_flags(
        args,
        value_flags={"--reason"},
        bool_flags={"--no-live-dispatch"},
        allow_positional=False,
    )
    if "--reason" not in values:
        raise WorktreeError("WORKTREE_SWEEP_REASON_REQUIRED")
    if "--no-live-dispatch" not in flags:
        raise WorktreeError(
            "WORKTREE_SWEEP_PRECONDITION_MISSING",
            "--no-live-dispatch が要る（live な dispatch が1つも無いことを観測した地点"
            "＝レートリミット復帰イベントからのみ呼ぶ）",
        )
    return SweepRequest(
        reason=_validate_reason(values["--reason"]), no_live_dispatch=True
    )


# --- パス検証 ------------------------------------------------------------------


def validate_worktree_path(value: str) -> str:
    """``.claude/worktrees/agent-<id>`` ちょうどの repo-root 相対パスだけを受理する。

    **正規化より先に ``..`` を見る**（正規化で吸収させない）。絶対パス・``~``・
    バックスラッシュ区切り・サブディレクトリ・要素4つ以上はすべて拒否する。
    ここは純粋な構文検査で、FS には一切触れない（symlink 等の検査は
    :func:`resolve_within` が担う）。
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("WORKTREE_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "worktree path")
    if value.startswith("~"):
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if value.startswith("/"):
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("WORKTREE_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("WORKTREE_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    normalized = "/".join(parts)
    if len(parts) != 3 or not WORKTREE_PATH_RE.fullmatch(normalized):
        raise WorktreeError("WORKTREE_PATH_SHAPE_INVALID", value)
    return normalized


def validate_handoff_relpath(value: str, *, expected_issue: int | None = None) -> str:
    """handoff の「作業ツリールート相対」パスを6条件で検証する。

    `.claude/agents/issue-implementer.md` / `issue-fixer.md` の「``handoff_path`` の検査」と
    同一の規則（symlink 検査＝条件6 だけは FS を見るため :func:`resolve_within` が担当）:

    1. 相対パスであること（先頭 ``/``・``~``・ドライブレターを拒否）
    2. パス要素に ``..`` を含まないこと（正規化で吸収しない）
    3. ``tmp/_handoff/`` 直下のファイル1つであること（要素ちょうど3つ）
    4. ファイル名が ``<agent>--issue-<N>`` で始まり、``issue-<N>`` の直後が ``-`` か ``.``
       であること（``expected_issue`` を渡すと ``<N>`` の一致も見る）
    5. サフィックス部の文字種が ``[A-Za-z0-9._-]`` に限られること
    6. （FS 側）構成要素に symlink が無いこと
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("COLLECT_HANDOFF_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "handoff path")
    if value.startswith("~") or value.startswith("/"):
        raise WorktreeError("COLLECT_HANDOFF_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("COLLECT_HANDOFF_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("COLLECT_HANDOFF_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("COLLECT_HANDOFF_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    if len(parts) != 3 or tuple(parts[:2]) != HANDOFF_DIR_PARTS:
        raise WorktreeError("COLLECT_HANDOFF_PATH_SHAPE_INVALID", value)
    match = HANDOFF_FILENAME_RE.fullmatch(parts[2])
    if match is None:
        raise WorktreeError("COLLECT_HANDOFF_FILENAME_INVALID", parts[2])
    if expected_issue is not None and int(match.group("issue")) != int(expected_issue):
        raise WorktreeError(
            "COLLECT_HANDOFF_ISSUE_MISMATCH",
            f"expected issue {expected_issue}; filename says {match.group('issue')}",
        )
    return "/".join(parts)


def validate_collect_dest(value: str) -> str:
    """``--into`` の「main worktree 相対」パスを検証する。

    書き先は ``tmp/_handoff/`` 配下に閉じる（回収物を任意の場所へ書けるようにしない）。
    ``tmp/_handoff/`` は ``dsv2 clean-tmp`` の保護対象なので、回収物が掃除で消えることもない。
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("COLLECT_DEST_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "destination path")
    if value.startswith("~") or value.startswith("/"):
        raise WorktreeError("COLLECT_DEST_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("COLLECT_DEST_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("COLLECT_DEST_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("COLLECT_DEST_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    if len(parts) < 3 or tuple(parts[:2]) != HANDOFF_DIR_PARTS:
        raise WorktreeError("COLLECT_DEST_PATH_SHAPE_INVALID", value)
    for part in parts[2:]:
        if not _SAFE_PATH_PART_RE.fullmatch(part):
            raise WorktreeError("COLLECT_DEST_PATH_SHAPE_INVALID", part)
    return "/".join(parts)


def resolve_within(root, relative: str, *, error: str = "WORKTREE_PATH_SYMLINK") -> Path:
    """``root`` 配下の ``relative`` を、**構成要素に symlink が無いこと**を確認しながら解決する。

    symlink 越しに repo 外へ誘導された読み書き／削除を許さない。実体解決後もなお ``root``
    配下であることを最後に確かめる（``root`` 自身が symlink 経由で与えられた場合の保険）。
    """
    base = Path(root).resolve()
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise WorktreeError(error, str(current))
    try:
        current.resolve().relative_to(base)
    except ValueError:
        raise WorktreeError("WORKTREE_PATH_ESCAPES_ROOT", str(current)) from None
    return current


# --- git 実行 ------------------------------------------------------------------


def _run_git(
    argv: Sequence[str],
    *,
    cwd,
    runner: Callable[..., subprocess.CompletedProcess],
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """``timeout``/``env`` は明示的に渡されたときだけ ``runner`` へ転送する。

    ネットワーク I/O が起こりうる呼び出し（``git fetch``）だけがこの2つを渡し、それ以外の
    純ローカル操作（``worktree list``/``worktree remove``/``branch -D`` 等）は従来どおり
    渡さない（Issue #426・F-426-05——ハングしうるのは fetch だけなので、対象を広げない）。
    """
    kwargs: dict = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if env is not None:
        kwargs["env"] = env
    return runner(
        list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False, **kwargs
    )


def _fetch_env() -> dict:
    """``git fetch`` を非対話化する env（stdin 経由の認証プロンプト待ちでハングしないため）。

    ``os.environ`` をコピーした上で ``GIT_TERMINAL_PROMPT=0`` を上書きする——他の環境変数
    （``PATH``/``GIT_SSH`` 等）を握り潰すと fetch 自体が動かなくなる呼び出し環境がありうるため、
    既存 env を丸ごと引き継いだ上でこの1変数だけを足す。
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def worktree_records(repo_root, *, runner: Callable[..., subprocess.CompletedProcess]) -> list:
    """``git worktree list --porcelain`` を ``{path, branch, locked}`` のレコード列にする。

    **先頭レコードは main worktree（primary checkout）** で、以降が linked worktree
    （porcelain の仕様）。``locked`` は ``locked`` 行（理由付きの ``locked <reason>`` を含む）の
    有無で決める——ハーネスが live な agent worktree をロックする構成では、この印が
    「今まさに動いている dispatch のもの」を示す観測になる（Issue #502）。

    パーサをここ1箇所に集約する（:func:`linked_worktree_paths` も本関数を使う）。同じ
    porcelain を2箇所で別々に読むと、片方だけが ``locked`` を見落とす類のズレが生まれる。
    """
    completed = _run_git(
        ["git", "worktree", "list", "--porcelain"], cwd=repo_root, runner=runner
    )
    if completed.returncode != 0:
        raise WorktreeError("WORKTREE_GIT_ERROR", "worktree list")
    records: list = []
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("worktree "):
            records.append(
                {
                    "path": stripped[len("worktree "):].strip(),
                    "branch": None,
                    "locked": False,
                }
            )
            continue
        if not records:
            continue
        if stripped.startswith("branch "):
            records[-1]["branch"] = stripped[len("branch "):].strip()
        elif stripped == "locked" or stripped.startswith("locked "):
            records[-1]["locked"] = True
    return records


def linked_worktree_paths(repo_root, *, runner: Callable[..., subprocess.CompletedProcess]) -> list:
    """``git worktree list --porcelain`` が返す **linked** worktree の絶対パス一覧。

    porcelain の最初のレコードは main worktree なので除く（main を ``worktree remove`` の
    対象にできないようにする）。
    """
    return [record["path"] for record in worktree_records(repo_root, runner=runner)][1:]


def _is_git_managed(target: Path, repo_root, *, runner) -> bool:
    resolved = target.resolve()
    for candidate in linked_worktree_paths(repo_root, runner=runner):
        try:
            if Path(candidate).resolve() == resolved:
                return True
        except OSError:
            continue
    return False


# --- 台帳参照 ------------------------------------------------------------------


def _entries(repo_root) -> list:
    try:
        return read_ledger(repo_root)["entries"]
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc


def find_entry(repo_root, *, entry_id: str | None = None, worktree_path: str | None = None):
    """``entry_id`` 優先、無ければ ``worktree_path`` で**最新の**エントリを引く。"""
    entries = _entries(repo_root)
    if entry_id is not None:
        for entry in entries:
            if entry.get("entry_id") == entry_id:
                return entry
        return None
    if worktree_path is not None:
        for entry in reversed(entries):
            if entry.get("worktree_path") == worktree_path:
                return entry
    return None


def _mark(repo_root, entry_id: str, status: str, *, now, note: str = "", collected_to=None) -> None:
    try:
        mark(repo_root, entry_id, status, now=now, note=note, collected_to=collected_to)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc


def _note(repo_root, entry_id: str, *, now, note: str) -> None:
    """状態を変えずに notes へ1行残す（受理した ``--reason`` を落とさないため）。"""
    if not note:
        return
    try:
        add_note(repo_root, entry_id, now=now, note=note)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc


def _cleanup_branch_ref(repo_root, entry, *, now, runner: Callable[..., subprocess.CompletedProcess]) -> None:
    """worktree 実体の削除**後**に、台帳の ``branch_name`` に対応するローカル ref の削除を
    試みる（Issue #426・F-426-01 で安全化）。

    ``git branch -D`` は force delete であり、未 push のコミットを reflog ごと黙って
    破棄しうる。削除の前に fresh fetch した ``refs/remotes/origin/<branch_name>`` に対して
    ローカル ref の tip が祖先であることを ``git merge-base --is-ancestor`` で確認し、祖先で
    ない・判定不能（fetch/merge-base 自体の失敗・origin 側 ref が無い等）の場合は削除せずに
    スキップし、理由を ``_note()`` に残す。

    fetch の呼び出しには ``timeout=FETCH_TIMEOUT_SECONDS`` と ``GIT_TERMINAL_PROMPT=0`` を
    渡す（Issue #426・F-426-05）。到達不能な origin や認証プロンプト待ちで
    ``worktree_release()`` 全体が無期限にハングすることを防ぐ——タイムアウトも他の fetch 失敗と
    同様にスキップ＋ ``_note()`` 記録として扱い、フェイルオープン契約は変えない。

    このブランチが他の worktree に checked out されている場合の安全網は ``git branch -D``
    自身の拒否に委ねる（``git worktree remove`` の成功が保証するのは「この worktree がもう
    branch_name を掴んでいない」ことだけで、別の linked worktree の不在までは含意しない）。

    **フェイルオープン**：削除・スキップいずれの結果でも ``worktree_release()`` 全体は
    失敗させない（worktree 実体の削除が本義務で、ローカル ref の削除は副次的な後始末）。
    ただし成否・スキップ理由は必ず ``_note()`` で台帳に残す——黙って握り潰さない。削除されず
    残った stray ref の安全網は ``gitgate/adopt.py`` の ``adopt_branch()`` が持つ tip 一致
    検査（無害なら reclaim、そうでなければ ``BRANCH_ADOPT_LOCAL_EXISTS`` へ fail-close）。
    """
    if entry is None:
        return
    branch_name = entry.get("branch_name")
    entry_id = entry.get("entry_id")
    if not branch_name or entry_id is None:
        return

    def _skip(reason: str) -> None:
        _note(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"worktree-release: ローカルブランチ ref {branch_name} の削除を"
                f"スキップした（{reason}）"
            ),
        )

    try:
        fetch_result = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=repo_root,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except subprocess.TimeoutExpired:
        # フェイルオープン: 到達不能/認証待ちの origin で無期限にハングしない
        # （Issue #426・F-426-05）。worktree_release() 自体は失敗させず、理由だけ記録する。
        _skip(f"origin の fetch がタイムアウトした（{FETCH_TIMEOUT_SECONDS}秒）")
        return
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        _skip(f"origin の fetch に失敗: {str(exc)[:200]}")
        return
    if fetch_result.returncode != 0:
        _skip(f"origin の fetch に失敗: {(fetch_result.stderr or '').strip()[:200]}")
        return

    try:
        ancestor_check = _run_git(
            [
                "git", "merge-base", "--is-ancestor",
                f"refs/heads/{branch_name}", f"refs/remotes/origin/{branch_name}",
            ],
            cwd=repo_root,
            runner=runner,
        )
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        _skip(f"origin 包含の判定に失敗: {str(exc)[:200]}")
        return
    if ancestor_check.returncode != 0:
        _skip(f"origin/{branch_name} に含まれない、または判定不能")
        return

    try:
        result = _run_git(["git", "branch", "-D", branch_name], cwd=repo_root, runner=runner)
        ok = result.returncode == 0
        detail = "" if ok else (result.stderr or "").strip()[:200]
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        ok = False
        detail = str(exc)[:200]
    if ok:
        note = f"worktree-release: ローカルブランチ ref {branch_name} を削除した"
    else:
        note = f"worktree-release: ローカルブランチ ref {branch_name} の削除に失敗した（{detail}）"
    _note(repo_root, entry_id, now=now, note=note)


def _reason_note(verb: str, reason: str, *, flag: str = "") -> str:
    """受理した ``--reason`` を notes 用の1行に整形する（空 reason なら空文字）。

    **受理・検証まで通った ``--reason`` は必ず台帳に残す**（F-354-04）。``--force-uncollected`` /
    ``--allow-missing-handoff`` と一緒に渡されたときだけ記録する作りだと、単独で渡された理由が
    「記録された」と誤認されたまま失われる（PR8 区分1 が保全対象とする一次情報の取りこぼし）。
    """
    if not reason:
        return ""
    return f"{verb} {flag}: {reason}" if flag else f"{verb}: {reason}"


# --- 実体の削除 ----------------------------------------------------------------


def _is_worktree_lock_failure(detail: str | None) -> bool:
    """``git worktree remove`` の失敗が **worktree ロック**由来か（Issue #464・F-464-01 是正）。

    停止途中のエージェントプロセスが worktree を掴んだままだと
    ``fatal: cannot remove a locked working tree, lock reason: ...`` で失敗する。
    git のロック時メッセージは版差があるが、いずれも "locked working tree" または
    "locked worktree" という**連結した語句**を含む。この判定は連結一致に絞る——
    「"lock" と "working tree"/"worktree" がそれぞれ独立に含まれるか」を見ていた旧実装は、
    削除対象パスが常に ``.claude/worktrees/agent-<id>`` を含むため後半の条件がほぼ常に真になり
    実効条件が ``"lock" in stderr`` だけに縮退していた（F-464-01）。結果として
    ``fatal: Unable to create '<repo>/.git/worktrees/agent-x/index.lock': File exists.`` の
    ような ``index.lock``（別レイヤのロック＝非 worktree ロック失敗）も誤って worktree ロック
    と判定し、本来 ``stale``（``ISSUE_START_WORKTREE_RESIDUE`` で解消コマンド付き deny）へ
    落ちるべきものが ``release_pending``（deny 網の外）へ落ちうる不具合があった。連結一致に
    絞ることで、``index.lock`` 等の別レイヤのロックは "locked working tree"/"locked worktree"
    を含まないため誤マッチしない。ロック以外の削除失敗（権限・submodule 等）は対象にしない
    ——それらは従来どおり ``WORKTREE_REMOVE_FAILED`` を送出して fail-close させる。
    """
    if not detail:
        return False
    lowered = detail.lower()
    return "locked working tree" in lowered or "locked worktree" in lowered


def _remove_worktree_dir(repo_root, relative: str, *, runner) -> bool:
    """``relative`` の実体を削除する。既に無ければ ``False``（冪等）。

    「何を消してよいか」の判定はここに集約する——``resolve_within``（構成要素の symlink 検査＋
    repo-root 外への脱出検査）と ``git worktree list --porcelain`` への登録確認の**両方**を
    通ったパスだけが ``git worktree remove`` に渡る。呼び出し側は「消してよい状態か」だけを
    判断し、「消してよいパスか」の判断は持たない。
    """
    target = resolve_within(repo_root, relative)
    if not target.exists():
        # 既に無い＝解放済みとみなす（`git worktree remove` の失敗を冪等化する）。
        _run_git(["git", "worktree", "prune"], cwd=repo_root, runner=runner)
        return False
    if not target.is_dir():
        raise WorktreeError("WORKTREE_PATH_NOT_DIR", str(target))
    if not _is_git_managed(target, repo_root, runner=runner):
        raise WorktreeError(
            "WORKTREE_NOT_GIT_MANAGED",
            f"{relative}（git の linked worktree として登録されていない）",
        )
    removed = _run_git(
        ["git", "worktree", "remove", "--force", str(target)], cwd=repo_root, runner=runner
    )
    if removed.returncode != 0:
        raise WorktreeError("WORKTREE_REMOVE_FAILED", (removed.stderr or "").strip()[:400])
    _run_git(["git", "worktree", "prune"], cwd=repo_root, runner=runner)
    return True


# --- verb: worktree-release ----------------------------------------------------


def worktree_release(
    repo_root,
    worktree_path: str,
    *,
    entry_id: str | None = None,
    force_uncollected: bool = False,
    reason: str = "",
    now,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    cleanup_branch_ref: bool = True,
) -> ReleaseOutcome:
    """linked worktree を冪等に解放する（FR-W5）。

    ``cleanup_branch_ref``（既定 ``True``・Issue #464 F-464-06）: worktree 実体の削除に
    成功した後の :func:`_cleanup_branch_ref`（``git fetch`` を伴うローカル ref 削除）を
    呼ぶかどうか。``issue-start-gate`` の毎 dispatch 経路（
    :func:`issue_start.gate._finish_deferred_releases`）は ``False`` を渡し、ネットワーク
    I/O を毎 dispatch のホットパスから除く——``SessionStart`` フックが**別途**
    ``cleanup_branch_ref=True``（既定）でフル掃除を行う。``git worktree remove`` 自体は
    ローカル操作でロック時は即失敗するため安価であり、mid-session の削除試行を止める理由には
    ならない。ネットワーク I/O だけを毎 dispatch のホットパスから外す。

    判定順序に意味がある——**状態判定はパス構文検査の直後・FS/git 操作より前**に済ませる。
    こうすると「消してはいけないもの（``running``）」に対して git が一切呼ばれないし、
    既に解放済み（``released``/``abandoned``）なら worktree が実在しなくても exit 0 で返せる。

    ================  ====================================================
    台帳の ``status``   挙動
    ================  ====================================================
    ``running``       拒否 ``WORKTREE_LIVE``（``--force-*`` でも上書き不可）
    ``open``          拒否 ``WORKTREE_NOT_BOUND``
    ``stopped``       拒否 ``WORKTREE_NOT_COLLECTED``（``--force-*`` でも上書き不可）
    ``collected``     実行 → ``released``
    ``release_pending`` 実行 → ``released``（回収済み・削除だけロックで遅延していた・Issue #464。
                      worktree が既に消えていれば冪等 no-op で ``released``）
    ``stale``         ``--force-uncollected --reason`` 必須
    ``released`` /
    ``abandoned``     台帳は進めない。**実体が残っていれば削除する**（残っていなければ no-op）
    エントリ無し       ``--force-uncollected --reason`` 必須（孤児 worktree の掃除経路）
    ================  ====================================================

    ``stopped`` に ``stale`` のような ``--force-uncollected`` の逃げ道を設けないのは、
    ``stopped``＝「まだ回収を試みていない」・``stale``＝「回収を試みて失敗した」で意味が違うから
    （同じ強制解除ボタンを共有すると両者の区別が消える）。``stopped`` は
    :func:`collect_worktree` で回収してから解放する。

    終端状態（``released`` / ``abandoned``）でも**ディスクを見る**（F-354-02）。
    ``worktree-forget`` は台帳を ``abandoned`` にするだけで worktree を消さないので、
    ここで実体を見ずに早期 return すると、forget 済みで残った worktree を削除する経路が
    リポジトリのどこにも無くなる（PR-3 の unclaimed deny が恒久化する）。台帳の状態は
    進めない——``abandoned`` は終端であり、``released`` へ動かすと「諦めた」記録が消える。
    """
    relative = validate_worktree_path(worktree_path)
    if entry_id is not None:
        _validate_entry_id(entry_id)
    if force_uncollected or reason:
        _validate_reason(reason)

    entry = find_entry(repo_root, entry_id=entry_id, worktree_path=relative)
    if entry_id is not None and entry is None:
        raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)
    if entry is not None:
        bound = entry.get("worktree_path")
        if bound is not None and bound != relative:
            # `--entry` と `<worktree-path>` が別のものを指している＝どちらが正か決められない。
            # 推測して片方を消すと「別 dispatch の worktree を消す」最悪形になるので止める。
            raise WorktreeError(
                "WORKTREE_ENTRY_PATH_MISMATCH", f"entry={bound}; argument={relative}"
            )

    status = entry.get("status") if entry is not None else None
    resolved_entry_id = entry.get("entry_id") if entry is not None else None
    note = _reason_note(
        "worktree-release",
        reason,
        flag="--force-uncollected" if force_uncollected else "",
    )

    if status in ("released", "abandoned"):
        # 台帳は終端。だが実体が残っていれば消す（唯一の削除経路・docstring 参照）。
        removed = _remove_worktree_dir(repo_root, relative, runner=runner)
        if resolved_entry_id is not None:
            if removed:
                _note(
                    repo_root,
                    resolved_entry_id,
                    now=now,
                    note=f"worktree-release: 終端状態（{status}）の残留実体を削除した",
                )
                if cleanup_branch_ref:
                    _cleanup_branch_ref(repo_root, entry, now=now, runner=runner)
            _note(repo_root, resolved_entry_id, now=now, note=note)
        return ReleaseOutcome(relative, resolved_entry_id, removed=removed, status=status)

    if status == "running":
        raise WorktreeError(
            "WORKTREE_LIVE",
            f"{relative}（live な dispatch が所有している。--force-uncollected でも解放しない）",
        )
    if status == "open":
        raise WorktreeError(
            "WORKTREE_NOT_BOUND",
            f"{relative}（worktree がまだ束縛されていない＝解放対象を特定できない）",
        )
    if status == "stopped":
        raise WorktreeError(
            "WORKTREE_NOT_COLLECTED",
            f"{relative}（所有者は停止したがまだ回収していない。collect-worktree で回収する"
            "＝--force-uncollected では上書きしない）",
        )
    if status == "stale" and not force_uncollected:
        raise WorktreeError(
            "WORKTREE_NOT_COLLECTED",
            f"{relative}（回収されていない。--force-uncollected --reason <text> が要る）",
        )
    if entry is None and not force_uncollected:
        raise WorktreeError(
            "WORKTREE_ORPHAN_REQUIRES_FORCE",
            f"{relative}（台帳にエントリが無い。--force-uncollected --reason <text> が要る）",
        )

    removed = _remove_worktree_dir(repo_root, relative, runner=runner)
    if resolved_entry_id is not None:
        _mark(repo_root, resolved_entry_id, "released", now=now, note=note)
        if removed and cleanup_branch_ref:
            _cleanup_branch_ref(repo_root, entry, now=now, runner=runner)
    return ReleaseOutcome(relative, resolved_entry_id, removed=removed, status="released")


# --- verb: collect-worktree ----------------------------------------------------


def _read_handoff(source: Path, *, max_bytes: int) -> bytes:
    """``O_NOFOLLOW`` で開き、regular file であることを fd 経由で確かめてから読む。

    ``lstat`` → ``open`` の2段だと間に差し替えられる（TOCTOU）。``O_NOFOLLOW`` は
    「最終要素が symlink なら開かない」を kernel 側で保証し、``fstat`` は**開いた当の
    inode** の種別を返すので、検査と読み取りが同じ実体を指すことが構造的に決まる。
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(source), flags)
    except OSError as exc:
        raise WorktreeError("COLLECT_HANDOFF_UNREADABLE", f"{source}: {exc.strerror}") from exc
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            raise WorktreeError("COLLECT_HANDOFF_NOT_REGULAR_FILE", str(source))
        if stat_result.st_size > max_bytes:
            raise WorktreeError(
                "COLLECT_HANDOFF_TOO_LARGE", f"{stat_result.st_size} > {max_bytes}"
            )
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read(max_bytes + 1)
    finally:
        if fd >= 0:
            os.close(fd)


def _write_collected(dest: Path, data: bytes) -> None:
    """``O_CREAT|O_EXCL`` で作る。既存なら ``COLLECT_DEST_EXISTS``（上書きしない＝消さない）。"""
    try:
        fd = os.open(str(dest), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise WorktreeError("COLLECT_DEST_EXISTS", str(dest)) from exc
    except OSError as exc:
        raise WorktreeError("COLLECT_WRITE_ERROR", f"{dest}: {exc.strerror}") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def _ensure_collected_dir(repo_root, relative_dir: str) -> Path:
    base = Path(repo_root).resolve()
    current = base
    for part in relative_dir.split("/"):
        current = current / part
        if current.is_symlink():
            raise WorktreeError("COLLECT_DEST_SYMLINK", str(current))
        if not current.exists():
            current.mkdir(parents=False)
        elif not current.is_dir():
            raise WorktreeError("COLLECT_DEST_NOT_DIR", str(current))
    return current


def collect_worktree(
    repo_root,
    *,
    entry_id: str | None = None,
    worktree_path: str | None = None,
    handoff_path: str | None = None,
    into: str | None = None,
    allow_missing_handoff: bool = False,
    reason: str = "",
    now,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    max_bytes: int = DEFAULT_MAX_HANDOFF_BYTES,
    release: bool = True,
) -> CollectOutcome:
    """handoff を回収してから worktree を解放する1操作（候補D・FR-W2）。

    段（**前段が失敗したら後段を実行しない**）:

    1. 対象特定（台帳 or 明示指定 ＋ パス6条件検査 ＋ ``--entry`` と ``<worktree-path>`` の一致検査）
    2. 回収元を読む（regular file・上限バイト数）
    3. 回収先へ ``O_CREAT|O_EXCL`` で書く
    4. 読み返して sha256 一致を確認
    5. 台帳を ``collected`` へ（``collected_to`` を記録）
    6. :func:`worktree_release` を呼んで ``released`` へ

    「回収に失敗したのに解放が走る」ことは、検査ではなく**この呼び出し順序**が防ぐ
    ——2〜4 のいずれかが例外を投げれば 6 に到達しない。

    **回収は済んだが段6 の ``git worktree remove`` が worktree ロックで失敗した場合**
    （Issue #464）は例外を送出せず、エントリを ``release_pending`` にして
    ``CollectOutcome(released=False)`` を返す。成果物は段3〜5 で ``collected_to`` へ退避済み
    で失われておらず、ロック（停止途中のエージェントプロセスが保持）はエージェントが完全に
    終了すれば外れる。実体の削除は次 dispatch で ``issue-start-gate`` が引き取る
    （:func:`issue_start.gate.assert_no_worktree_residue`）。**回収が成功していない経路
    （``collected_to`` 無し）／ロック以外の削除失敗では従来どおり例外を送出する**——
    fail-close は弱めない。

    **``--entry`` と ``<worktree-path>`` の食い違いは段1 で止める**（F-354-03）。この検査が
    段6（``worktree_release`` 内）にしか無いと、別 worktree の handoff を回収して回収先に書き、
    台帳を ``collected`` と誤記録した**後で**落ちる——後続の ``worktree-release`` が未回収の
    worktree を「回収済み」と誤認して削除しうる（FR-W2 の破れ＝handoff 喪失）。FS と台帳への
    副作用が1つでも起きる前に止める。

    受理する台帳の状態は ``stopped``（所有者停止済み・未回収）/ ``stale``（回収失敗）/
    ``collected``（回収済み・解放のみ）/ ``release_pending``（回収済み・削除だけロック失敗・
    段6 だけをやり直す）とエントリ無し。``running`` は拒否する
    ——live な dispatch の worktree は回収も解放もしない（安全側の既定）。

    ``release``（既定 ``True``）を偽にすると**段1〜5 だけを実行して段6 を飛ばす**。
    「回収は必ず先に済ませたいが、解放してよいかは回収後に追加で判定したい」呼び出し元
    （:func:`_sweep_one` の clean 検査＝Issue #502 F-502-01）のための分割点である。偽で
    返ったときエントリは ``collected`` に留まり、成果物は ``collected_to`` へ退避済み。
    解放したくなったら**同じ引数でもう一度呼べばよい**——``collected`` は段2〜5 を飛ばして
    段6 だけを実行するので、``release_pending`` への遅延（Issue #464）を含む解放段の契約を
    そのまま再利用できる。
    """
    if entry_id is not None:
        _validate_entry_id(entry_id)
    if allow_missing_handoff or reason:
        _validate_reason(reason)

    # --- 段1: 対象特定 ---
    entry = None
    if entry_id is not None:
        entry = find_entry(repo_root, entry_id=entry_id)
        if entry is None:
            raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)

    relative_worktree = worktree_path
    if relative_worktree is None and entry is not None:
        relative_worktree = entry.get("worktree_path")
    if not relative_worktree:
        raise WorktreeError(
            "COLLECT_WORKTREE_UNKNOWN",
            f"{entry_id}（台帳の worktree_path が未束縛。<worktree-path> を明示する）",
        )
    relative_worktree = validate_worktree_path(relative_worktree)
    if entry is not None:
        bound = entry.get("worktree_path")
        if bound is not None and bound != relative_worktree:
            # `--entry` と `<worktree-path>` が別のものを指している＝どちらが正か決められない。
            # **FS も台帳も一切触る前に**止める（F-354-03。段6 まで進むと、別 worktree の
            # handoff を回収した上で「回収済み」と誤記録した後で落ちることになる）。
            raise WorktreeError(
                "WORKTREE_ENTRY_PATH_MISMATCH", f"entry={bound}; argument={relative_worktree}"
            )
    if entry is None:
        # `--entry` 無しの明示指定でも、同じ worktree を指す台帳エントリがあればそれに従う
        # （段6 の解放判定と段5 の記録が別のものを見ると、状態が食い違う）。
        entry = find_entry(repo_root, worktree_path=relative_worktree)

    status = entry.get("status") if entry is not None else None
    if status in ("released", "abandoned"):
        # 回収する対象がもう無い（終端状態）。実体が残っている場合の削除は
        # `worktree-release` の担当（F-354-02）で、回収 verb はここでは何もしない。
        return CollectOutcome(
            relative_worktree, entry.get("entry_id"), entry.get("collected_to"), released=False
        )
    if status == "running":
        raise WorktreeError(
            "WORKTREE_LIVE",
            f"{relative_worktree}（live な dispatch が所有している。停止してから回収する）",
        )
    if status == "open":
        raise WorktreeError("WORKTREE_NOT_BOUND", relative_worktree)

    resolved_entry_id = entry.get("entry_id") if entry is not None else None
    collected_to = entry.get("collected_to") if entry is not None else None
    reason_recorded = False

    # `collected`（回収済み・解放のみ）と `release_pending`（回収済み・削除だけ git ロックで
    # 失敗した・Issue #464）はどちらも回収段を飛ばして段6 だけをやり直す。
    if status not in ("collected", DEFERRED_RELEASE_STATUS):
        relative_handoff = handoff_path
        if relative_handoff is None and entry is not None:
            relative_handoff = entry.get("handoff_path")
        if not relative_handoff:
            if not allow_missing_handoff:
                raise WorktreeError(
                    "COLLECT_HANDOFF_UNKNOWN",
                    "handoff の相対パスが判らない（--handoff か --allow-missing-handoff が要る）",
                )
        else:
            expected_issue = entry.get("issue") if entry is not None else None
            relative_handoff = validate_handoff_relpath(
                relative_handoff, expected_issue=expected_issue
            )

        worktree_dir = resolve_within(repo_root, relative_worktree)

        # --- 段2: 回収元を読む ---
        data: bytes | None = None
        if relative_handoff:
            source = resolve_within(
                worktree_dir, relative_handoff, error="COLLECT_HANDOFF_SYMLINK"
            )
            if not source.exists():
                if not allow_missing_handoff:
                    raise WorktreeError("COLLECT_HANDOFF_MISSING", str(source))
            else:
                data = _read_handoff(source, max_bytes=max_bytes)
                if len(data) > max_bytes:
                    raise WorktreeError("COLLECT_HANDOFF_TOO_LARGE", str(max_bytes))

        # --- 段3〜4: 書いて読み返して検証 ---
        if data is not None:
            if into is not None:
                relative_dest = validate_collect_dest(into)
            else:
                key = resolved_entry_id or relative_worktree.rsplit("/", 1)[-1]
                basename = relative_handoff.rsplit("/", 1)[-1]
                relative_dest = "/".join(
                    (*HANDOFF_DIR_PARTS, COLLECTED_DIRNAME, f"{key}--{basename}")
                )
            parent_rel, _, filename = relative_dest.rpartition("/")
            directory = _ensure_collected_dir(repo_root, parent_rel)
            dest = directory / filename
            if dest.is_symlink():
                raise WorktreeError("COLLECT_DEST_SYMLINK", str(dest))
            _write_collected(dest, data)
            expected_digest = hashlib.sha256(data).hexdigest()
            actual_digest = hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual_digest != expected_digest:
                # 検証に落ちたら**解放へ進まない**。壊れた回収物を残すと O_EXCL で再試行が
                # 詰まるだけなので取り除く（保全対象の記録ではなく失敗した中間生成物）。
                try:
                    dest.unlink()
                except OSError:
                    pass
                raise WorktreeError(
                    "COLLECT_VERIFY_MISMATCH",
                    f"{relative_dest}: expected {expected_digest}; actual {actual_digest}",
                )
            collected_to = relative_dest

        # --- 段5: 台帳を collected へ ---
        if resolved_entry_id is not None:
            note = _reason_note(
                "collect-worktree",
                reason,
                flag="--allow-missing-handoff" if data is None else "",
            )
            reason_recorded = bool(note)
            _mark(
                repo_root,
                resolved_entry_id,
                "collected",
                now=now,
                note=note,
                collected_to=collected_to,
            )

    # 受理した `--reason` を1度も台帳へ書いていない経路（回収に成功した場合・既に collected
    # だった場合）でも必ず残す（F-354-04）。段6 側では記録しない——エントリがあるときの
    # 解放は状態遷移の一部で、理由は「回収の理由」として collect 側に属するため。
    if resolved_entry_id is not None and not reason_recorded:
        _note(
            repo_root,
            resolved_entry_id,
            now=now,
            note=_reason_note("collect-worktree", reason),
        )

    # --- 段6: 解放 ---
    if not release:
        # 呼び出し元が「解放してよいか」を回収後に追加判定する（F-502-01 の clean 検査）。
        # 段1〜5 は完了済み＝成果物は `collected_to` へ退避済みなので、ここで止めても失う
        # ものは無い。エントリは `collected` のままなので、解放したくなったら同じ呼び出しを
        # もう一度行えば段6 だけが走る。
        return CollectOutcome(
            relative_worktree, resolved_entry_id, collected_to, released=False
        )
    try:
        outcome = worktree_release(
            repo_root,
            relative_worktree,
            entry_id=resolved_entry_id,
            force_uncollected=resolved_entry_id is None,
            # 台帳エントリが無い＝`--force-uncollected` が要る経路だけ理由を渡す（エントリが
            # ある場合の理由は直前で記録済みなので、ここで渡すと同じ理由が2回 notes に載る）。
            reason=(
                (reason or "collect-worktree: 台帳エントリの無い worktree を回収後に解放")
                if resolved_entry_id is None
                else ""
            ),
            now=now,
            runner=runner,
        )
    except WorktreeError as exc:
        # 回収（コピー＋sha 検証＋台帳 `collected` 記録）は完了しているのに `git worktree
        # remove` だけが失敗した（Issue #464）。典型は、停止途中のエージェントプロセスが
        # まだ worktree を git ロックしている `WORKTREE_REMOVE_FAILED`。成果物は
        # `collected_to`（main worktree 側の tmp/_handoff/collected/）へ退避済みで失われて
        # いないので、**削除だけを後段へ遅延する**：エントリを `release_pending` にして
        # `ISSUE_START_WORKTREE_RESIDUE` の対象から外し（成果物が安全なのに次 dispatch を
        # 止めない）、ロックが外れた後に `issue-start-gate` が削除を引き取る。
        # **回収が成功した経路に限る**——`collected_to` が無い／ロック以外の削除失敗では
        # 従来どおり例外を送出して fail-close する（取りこぼしを見逃さない）。
        if (
            resolved_entry_id is not None
            and collected_to is not None
            and exc.reason == "WORKTREE_REMOVE_FAILED"
            and _is_worktree_lock_failure(exc.detail)
        ):
            _mark(
                repo_root,
                resolved_entry_id,
                DEFERRED_RELEASE_STATUS,
                now=now,
                note=(
                    "collect-worktree: handoff は回収済み（collected_to）だが git の "
                    "worktree ロックで削除できなかった。削除を issue-start-gate へ遅延する"
                    f"（Issue #464 / {(exc.detail or '')[:160]}）"
                ),
            )
            return CollectOutcome(
                relative_worktree, resolved_entry_id, collected_to, released=False
            )
        raise
    return CollectOutcome(
        relative_worktree, resolved_entry_id, collected_to, released=outcome.status == "released"
    )


# --- verb: worktree-forget -----------------------------------------------------


def worktree_forget(repo_root, entry_id: str, *, reason: str, now) -> dict:
    """回収不能な ``stale`` エントリを ``abandoned`` へ逃がす（**worktree は消さない**）。

    PR-3 の deny が恒久的にパイプラインを止めるのを防ぐ唯一の逃げ道なので、``reason`` を
    必須にして「なぜ諦めたか」を必ず残す。**エントリは削除しない**（PR8 区分1＝保全対象）。

    ディスク上に実体が残っている場合は、この verb の**後で** :func:`worktree_release` を
    呼んで削除する（``abandoned`` のまま実体だけ消える）。この2手順以外に実体を消す経路は
    無い——回収の記録（``abandoned`` の理由）と実体の削除を1つの verb に混ぜない。
    """
    _validate_entry_id(entry_id)
    _validate_reason(reason)
    entry = find_entry(repo_root, entry_id=entry_id)
    if entry is None:
        raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)
    if entry.get("status") == "abandoned":
        # 冪等: 既に abandoned なら理由を1行足すだけ（状態機械は進めない）。
        try:
            add_note(repo_root, entry_id, now=now, note=f"worktree-forget (repeat): {reason}")
        except LedgerError as exc:
            raise WorktreeError(exc.reason, exc.detail) from exc
        return find_entry(repo_root, entry_id=entry_id)
    _mark(repo_root, entry_id, "abandoned", now=now, note=f"worktree-forget: {reason}")
    return find_entry(repo_root, entry_id=entry_id)


# --- verb: worktree-sweep-abandoned ---------------------------------------------

# 掃引で台帳へ残す marker（notes を grep すれば「なぜ解放されたか」が後から辿れる）。
SWEEP_MARKER = "worktree-sweep-abandoned"


def _own_handoff(repo_root, entry) -> tuple:
    """エントリの worktree から**その dispatch 自身の** handoff を1つに決める。

    返り値は ``(相対パス | None, how)``。``how`` は ``unique`` / ``empty`` / ``ambiguous`` /
    ``unreadable`` / ``unidentifiable``。判定規則は
    ``issue_start/subagent_hooks.py::_discover_handoff`` と同一（``<agent_type>--issue-<N>``
    に一致するものだけを自分の成果物とみなす）で、委譲先エージェントの handoff を自分のものと
    取り違えない（Issue #423 の実測）。**規則は同一だが実装は共有しない**——フック側は
    「``gitgate`` を import せず起動するだけ」という境界を保つために独自に組み立てており、
    こちらは ``gitgate`` 側の正本である :data:`HANDOFF_FILENAME_RE` をそのまま使う。
    """
    agent_type = entry.get("agent_type")
    issue = entry.get("issue")
    relative = entry.get("worktree_path")
    if not isinstance(agent_type, str) or not agent_type:
        return None, "unidentifiable"
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        return None, "unidentifiable"
    try:
        worktree_dir = resolve_within(repo_root, relative)
    except WorktreeError:
        return None, "unreadable"
    directory = worktree_dir / HANDOFF_DIR_PARTS[0] / HANDOFF_DIR_PARTS[1]
    if directory.is_symlink():
        return None, "unreadable"
    if not directory.exists():
        return None, "empty"
    if not directory.is_dir():
        return None, "unreadable"
    try:
        names = sorted(child.name for child in directory.iterdir() if not child.is_dir())
    except OSError:
        return None, "unreadable"
    mine = []
    for name in names:
        match = HANDOFF_FILENAME_RE.fullmatch(name)
        if match is None:
            continue
        if match.group("agent") != agent_type or int(match.group("issue")) != issue:
            continue
        mine.append(name)
    if not mine:
        return None, "empty"
    if len(mine) > 1:
        return None, "ambiguous"
    return f"{'/'.join(HANDOFF_DIR_PARTS)}/{mine[0]}", "unique"


def _is_worktree_clean(repo_root, entry, *, runner) -> tuple:
    """作業ツリーに未コミット/未追跡の変更が無いことを確認する（Issue #502・F-502-01）。

    返り値は ``(bool, 理由)``。真を返すのは ``git status --porcelain`` を実際に実行できて、
    その出力が空だったときだけ——**判定できなかったときは偽**（fail-close）。
    「見られなかった」を「捨ててよい」に潰さない。

    **この関門は handoff の有無で免除しない**。実体を消す :func:`_remove_worktree_dir` は
    ``git worktree remove --force`` を使い、dirty / untracked を問答無用で消す。handoff を
    書き終えていることは「作業ツリーに未コミットの何かが残っていない」ことを含意しないため、
    handoff がある経路（:func:`_sweep_one` の ``how == "unique"``）でも回収の**後で**必ず通す。
    """
    relative = entry.get("worktree_path")
    try:
        target = resolve_within(repo_root, relative)
    except WorktreeError as exc:
        return False, f"worktree のパスを解決できない（{exc.reason}）"
    if not target.is_dir():
        return False, "worktree の実体が無い"
    status = _run_git(["git", "status", "--porcelain"], cwd=target, runner=runner)
    if status.returncode != 0:
        return False, "git status を実行できない（判定不能）"
    if (status.stdout or "").strip():
        return False, "作業ツリーに未コミット/未追跡の変更がある"
    return True, ""


def _is_discardable(repo_root, entry, *, runner) -> tuple:
    """handoff が無い worktree を「捨ててよい」と**積極的に確認**する（Issue #502）。

    返り値は ``(bool, 理由)``。真を返すのは次の**すべて**を観測できたときだけで、1つでも
    観測できなければ偽（fail-close）——「判定できなかった」を「捨ててよい」に潰さない。

    1. 台帳に ``branch_name`` がある（origin 包含を判定する相手が決まる）。
    2. 作業ツリーが clean（:func:`_is_worktree_clean`）＝未コミットの変更も未追跡
       ファイルも無い。
    3. ``HEAD`` が fresh fetch 後の ``refs/remotes/origin/<branch_name>`` に含まれる
       ＝未 push のコミットが無い。

    これは Issue #502 で主文脈が手作業で確認した内容（「作業ツリー clean・HEAD が remote と
    同一・ハンドオフ未作成で、失われる作業は無かった」）を機械化したものである。
    条件2 は handoff がある経路でも必要なので :func:`_is_worktree_clean` へ切り出してある
    （F-502-01）。
    """
    relative = entry.get("worktree_path")
    branch_name = entry.get("branch_name")
    if not isinstance(branch_name, str) or not branch_name:
        return False, "台帳に branch_name が無く origin 包含を判定できない"
    clean, why = _is_worktree_clean(repo_root, entry, runner=runner)
    if not clean:
        return False, why
    try:
        target = resolve_within(repo_root, relative)
    except WorktreeError as exc:  # pragma: no cover - 直前の clean 検査が同じ解決に成功済み
        return False, f"worktree のパスを解決できない（{exc.reason}）"
    try:
        fetched = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=target,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except Exception as exc:  # noqa: BLE001 - 判定不能は「捨ててよい」に倒さない
        return False, f"origin の fetch に失敗した（{type(exc).__name__}）"
    if fetched.returncode != 0:
        return False, "origin の fetch に失敗した（判定不能）"
    ancestor = _run_git(
        [
            "git", "merge-base", "--is-ancestor",
            "HEAD", f"refs/remotes/origin/{branch_name}",
        ],
        cwd=target,
        runner=runner,
    )
    if ancestor.returncode != 0:
        return False, f"HEAD が origin/{branch_name} に含まれない（未 push のコミットがありうる）"
    return True, ""


def _locked_worktree_paths(repo_root, *, runner) -> set:
    """``locked`` と報告された worktree の解決済み絶対パス集合。"""
    locked = set()
    for record in worktree_records(repo_root, runner=runner):
        if not record.get("locked"):
            continue
        try:
            locked.add(str(Path(record["path"]).resolve()))
        except OSError:
            continue
    return locked


def sweep_abandoned_running(
    repo_root,
    *,
    now,
    reason: str,
    no_live_dispatch: bool = False,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list:
    """異常終了で ``running`` のまま残ったエントリを回収・解放する（Issue #502・観測1）。

    ``no_live_dispatch`` が偽なら**台帳も git も一切触らずに空を返す**。``running`` は
    「入れ子委譲待ちの正当な保留」でもあり（Issue #423）、状態だけでは異常終了と区別
    できないため、区別は呼び出し地点の観測（live な dispatch が1つも無い＝レートリミット
    復帰イベントで**当該ペインが**アイドル）に委ねる。その観測をこの引数として**明示的に**
    受け取ることで、「うっかり普通の dispatch 経路から呼ぶ」ことが構造的に無害化される。
    ただしこの観測が届くのは呼び出し元が見ている1ペインだけで、別ペインの live な dispatch を
    守るのは ``locked`` 判定である（モジュール docstring の ``worktree-sweep-abandoned`` 節）。

    掃引は entry ごとに独立で、1件の失敗が他を巻き込まない（例外を外へ出さない）。
    ``action`` の値:

    ==================  ==========================================================
    ``released``        回収（または捨ててよい確認）を経て worktree を解放した
    ``release-pending`` 回収は済んだが削除だけ git ロックで遅延した（Issue #464）
    ``kept-locked``     ``git worktree list`` が ``locked`` と報告した＝live とみなし触らない
    ``kept-unsafe``     捨ててよいと確認できなかった＝解放せず ``stale`` へ落とした
                        （handoff が無い場合は回収前の ``_is_discardable``、handoff がある
                        場合は**回収後**の clean 検査で落ちたもの＝F-502-01）
    ``kept-unresolved`` handoff を一意に決められない＝解放せず ``stale`` へ落とした
    ``kept-error``      回収・解放が失敗した＝``stale`` へ落とした
    ==================  ==========================================================

    ``stale`` へ落としたものは既存の ``ISSUE_START_WORKTREE_RESIDUE``（解消コマンド付き
    deny）が次 dispatch で拾う——**黙って残さない**。
    """
    if not no_live_dispatch:
        return []
    _validate_reason(reason)
    candidates = [
        entry
        for entry in _entries(repo_root)
        if entry.get("status") == "running"
        and isinstance(entry.get("entry_id"), str)
        and isinstance(entry.get("worktree_path"), str)
        and entry.get("worktree_path")
    ]
    if not candidates:
        return []
    try:
        locked = _locked_worktree_paths(repo_root, runner=runner)
    except Exception:  # noqa: BLE001 - 判定材料が読めないなら何もしない（fail-safe）
        return []

    outcomes: list = []
    for entry in candidates:
        entry_id = entry["entry_id"]
        relative = entry["worktree_path"]
        try:
            outcomes.append(
                _sweep_one(
                    repo_root,
                    entry,
                    now=now,
                    reason=reason,
                    locked=locked,
                    runner=runner,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 1件の事故で掃引全体を止めない
            outcomes.append(
                SweepEntryOutcome(
                    entry_id, relative, "kept-error", type(exc).__name__
                )
            )
    return outcomes


def _sweep_stale(repo_root, entry_id, *, now, note) -> None:
    try:
        _mark(repo_root, entry_id, "stale", now=now, note=note)
    except WorktreeError:
        # 記録できなくても掃引は続ける（残留は gate の deny が別途拾う）。
        pass


def _sweep_one(repo_root, entry, *, now, reason, locked, runner) -> SweepEntryOutcome:
    entry_id = entry["entry_id"]
    relative = entry["worktree_path"]
    try:
        resolved = str((Path(repo_root).resolve() / relative).resolve())
    except OSError:
        resolved = ""
    if resolved and resolved in locked:
        # ハーネスがロックしている＝live な dispatch が掴んでいる。触らない（#423 の保護）。
        return SweepEntryOutcome(
            entry_id, relative, "kept-locked", "git が locked と報告した worktree"
        )

    handoff, how = _own_handoff(repo_root, entry)
    if how in ("ambiguous", "unreadable", "unidentifiable"):
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 自分の handoff を一意に決められない（{how}）ため解放しない。"
                f"主文脈が collect-worktree / worktree-forget で処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-unresolved", how)

    if how == "empty":
        discardable, why = _is_discardable(repo_root, entry, runner=runner)
        if not discardable:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff が無く、捨ててよいと確認できなかったため解放しない"
                    f"（{why}）。主文脈が内容を確認して処置する（Issue #502）: {reason}"
                ),
            )
            return SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    _mark(
        repo_root,
        entry_id,
        "stopped",
        now=now,
        note=(
            f"{SWEEP_MARKER}: live な dispatch が1つも無い地点（レートリミット復帰）で "
            f"running が残っていたため、異常終了として停止を確定した（Issue #502・handoff={how}）"
            f": {reason}"
        ),
    )
    # 回収（段1〜5）と解放（段6）を分けて呼ぶ。**回収を先に確定させる**ことで、この後の
    # clean 検査で解放を止めても成果物は `collected_to` へ退避済みになる（F-502-01）。
    try:
        collected = collect_worktree(
            repo_root,
            entry_id=entry_id,
            handoff_path=handoff,
            allow_missing_handoff=handoff is None,
            reason=f"{SWEEP_MARKER}: {reason}",
            now=now,
            runner=runner,
            release=False,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 回収に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)

    if how == "unique":
        # handoff がある経路にも clean 検査を通す（F-502-01）。`git worktree remove --force`
        # は dirty/untracked を問答無用で消すため、「handoff が書けている＝完走した」を
        # 「捨ててよい」の代わりにしない。`how == "empty"` は上の `_is_discardable` で
        # 同じ検査（＋origin 包含）を既に通しているので二重には実行しない。
        clean, why = _is_worktree_clean(repo_root, entry, runner=runner)
        if not clean:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff は回収した"
                    f"（collected_to={collected.collected_to or '-'}）が、作業ツリーが clean と"
                    f"確認できなかったため解放しない（{why}）。主文脈が内容を確認して処置する"
                    f"（Issue #502）: {reason}"
                ),
            )
            return SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    # 段6 だけをやり直す（エントリは `collected`）。`release_pending` への遅延（Issue #464）を
    # 含む解放段の契約をそのまま再利用するため、`worktree_release` を直接呼ばない。
    # `reason` は回収段で既に台帳へ書いているので渡さない（同じ理由を2回 notes に載せない）。
    try:
        outcome = collect_worktree(
            repo_root,
            entry_id=entry_id,
            now=now,
            runner=runner,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 解放に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)
    return SweepEntryOutcome(
        entry_id,
        relative,
        "released" if outcome.released else "release-pending",
        outcome.collected_to or "",
    )


def default_repo_root(candidate=None) -> Path:
    """CLI 既定の repo-root（linked worktree から起動されても main worktree へ収束させる）。"""
    try:
        return main_worktree_root(Path.cwd() if candidate is None else candidate)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc
