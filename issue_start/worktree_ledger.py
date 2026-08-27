"""worktree 所有台帳（``<main-worktree>/tmp/_worktree/ledger.json``）（Issue #309・PR-1）。

**何を解く台帳か**: `issue-implementer` / `issue-fixer` の dispatch は
`isolation: "worktree"` の下で `.claude/worktrees/agent-<id>/` を占有するが、
「どの worktree が どの `{issue, agent_type, round, agent_id}` の dispatch のものか」は
どこにも機械可読な形で残っていない。残っていないため、

  * 終了した dispatch の worktree を安全に解放できない（誰のものか判らない）。
  * 残留した worktree を live な dispatch が掴んでしまう乗っ取り事象を検出できない。

本モジュールはこの束縛を**観測できる状態**として記録する（FR-W4）。

**本モジュール自身は worktree を1つも削除しない**——削除経路をこのモジュールは持たない
（構造的にゼロ）。実体を消すのは :mod:`gitgate.worktree` の ``worktree-release`` /
``collect-worktree`` だけである（PR-2）。本モジュールが持つのは**状態の記録と突き合わせ**で、
:func:`residue_report` が組み立てる evidence を dispatch の deny 判定へ使うのは
:mod:`issue_start.gate`（PR-3）。

置き場の決定（main worktree への収束）
------------------------------------
フックも gate も linked worktree から起動されうるため、``candidate`` をそのまま repo-root に
すると worktree ごとに台帳が分裂する。:func:`main_worktree_root` が ``.git`` ファイルの
``gitdir:`` → ``commondir`` を辿って必ず main worktree へ収束させる。

**この導出は ``karte/paths.py`` の :func:`main_worktree_root`（K-01）と同等のものを
本モジュール内に独立実装している**（選択肢 LG-1 案A・オーナー確定）。共有モジュール化しない
理由は、``karte/paths.py`` を Issue #318（``O_NOFOLLOW`` による symlink 再検査の原子化）が
触るため同一ファイルを本 PR も触ると衝突するから。加えて両者の fail-close ポリシーは将来
分岐しうる（台帳は書込専用・カルテは読書両用）ので、30行程度の重複が害になりにくい。
一次アンカーは ``karte/paths.py`` の K-01 docstring。

時刻の扱い（``.claude/rules/04-test-data.md`` 遵守）
--------------------------------------------------
* ``now`` は**必ず引数で注入する**。本モジュールは ``datetime.now()`` / ``time.time()`` を
  **一切呼ばない**。
* **TTL・経過時間による判定を1つも設けない**。判定は状態のみ（``status`` と実在の突き合わせ）。
  ``dispatched_at`` / ``closed_at`` は**診断用のスタンプであって判定入力ではない**。
  wall clock 比較が存在しないので、時間経過だけでテストが赤くなるクラスの問題が
  構造的に発生しない。
* ロック待ちのリトライも wall clock を読まない（``sleep`` 注入 × 固定回数）。

状態遷移（終端は ``released`` / ``abandoned``）
--------------------------------------------
    open ──SubagentStart で agent_id 束縛──▶ running ──SubagentStop：所有者停止を確認──▶ stopped
                                                                                          │
                                          回収成功 ├──▶ collected ──解放成功──▶ released
                                          回収失敗／判定不能 └──▶ stale
    stale ──(主文脈が collect-worktree で回収・解放)──▶ released
    stale ──(worktree-forget --reason)────────────▶ abandoned   ※理由必須・履歴に残す
    open  ──(SubagentStart が発火せず束縛できない)──▶ open のまま
    running / stopped ──(:func:`sweep_orphans`：worktree が実在しない)──▶ stale

``open`` は :func:`sweep_orphans` の対象に**含めない**（Issue #354・PR-3）。``open`` は
「dispatch を受理したが ``SubagentStart`` がまだ束縛していない」状態であり、**まさに今起動中の
dispatch**と「発火せず取り残された過去の dispatch」を、状態だけでは区別できない。区別するには
経過時間を読むしかなく、それは本モジュールが構造的に禁じている（下記「時刻の扱い」）。
``open`` を掃引すると live な dispatch のエントリを ``stale``＝強制解放の対象へ落としうるため
採らない。取り残された ``open`` は ``SubagentStop`` 側（:mod:`issue_start.subagent_hooks` の
解放段）が「自分の entry を引けなかった」ときに ``stale`` へ落とす——そこでは
「今まさに停止した dispatch のもの」という追加の観測がある。

``stopped`` は「**所有者の dispatch が停止したことを確認した**」という事実を機械可読に記録する
中間状態である（Issue #354 F-354-01）。``running`` から ``collected`` への直行辺は持たない
——``collected`` を作るのは ``collect-worktree`` 自身なので、直行辺があると
「回収する前に回収済みにしておく」以外に回収を始める手が無くなり、PR-3 の
``SubagentStop`` → ``collect-worktree --entry`` の経路が循環して成立しない。
停止確認を CLI フラグのような**記録されない signal** ではなく状態として持つのは、
「観測できないものは持たない」（`.claude/rules/01-principles.md`）に従うため。
``running`` は引き続き回収・解放のいずれからも拒否される（安全側の既定は弱めない）。

同一 status への遷移は no-op（冪等）。逆行遷移は ``LEDGER_ILLEGAL_TRANSITION`` で拒否する。
``abandoned`` は非終端状態のどこからでも遷移できる——``worktree-forget`` は PR-3 の deny が
恒久的にパイプラインを止めるのを防ぐ唯一の逃げ道であり、状態で塞いではならない。
**エントリは決して削除しない**（履歴として残す＝`.claude/rules/01-principles.md`
「PR8「消さない」の適用範囲」区分1）。

依存仕様:
  * ``karte/paths.py`` の :func:`main_worktree_root`（K-01・main worktree への収束）
  * ``dsv2/cleantmp.py`` docstring（``tmp/`` 配下の保護置き場のガード様式）
  ※ いずれも out-of-graph（版なし）のため補助ナビ。本モジュール自体は
    `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**区分（Issue 運用パイプライン）に属する。
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA_VERSION = "worktree-ledger/1"
STATUSES = ("open", "running", "stopped", "collected", "released", "stale", "abandoned")
TERMINAL_STATUSES = ("released", "abandoned")
UNRELEASED_STATUSES = ("open", "running", "stopped", "collected", "stale")
TMP_DIRNAME = "tmp"
LEDGER_DIRNAME = "_worktree"
LEDGER_FILENAME = "ledger.json"
LEDGER_LOCK_FILENAME = "ledger.json.lock"
LEDGER_TMP_FILENAME = "ledger.json.new"
WORKTREE_ROOT_REL = ".claude/worktrees"
AGENT_DIR_RE = re.compile(r"^agent-[A-Za-z0-9_-]{1,64}$")
WORKTREE_PATH_RE = re.compile(r"^\.claude/worktrees/agent-[A-Za-z0-9_-]{1,64}$")
ENTRY_ID_RE = re.compile(r"^wl-[0-9a-f]{12}$")
AGENT_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# ロック待ちの刻み幅。**wall clock を読まない**ため、待ち時間は
# 「この刻み × 試行回数」で表現する（`sleep` 注入でテストは実時間に依存しない）。
LOCK_RETRY_INTERVAL_S = 0.05

# 許可する遷移（自分自身＝冪等 no-op を含む）。ここに無い組は逆行遷移として拒否する。
_TRANSITIONS: Mapping[str, frozenset] = {
    "open": frozenset({"open", "running", "stale", "abandoned"}),
    # `running` から `collected` への直行辺は持たない（モジュール docstring 参照）。
    "running": frozenset({"running", "stopped", "stale", "abandoned"}),
    "stopped": frozenset({"stopped", "collected", "stale", "abandoned"}),
    "collected": frozenset({"collected", "released", "stale", "abandoned"}),
    "stale": frozenset({"stale", "collected", "released", "abandoned"}),
    "released": frozenset({"released"}),
    "abandoned": frozenset({"abandoned"}),
}


class LedgerError(Exception):
    """台帳を一意に読めない/書けない fail-close error（``reason`` と ``detail`` を持つ）。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


# --- パス解決 ------------------------------------------------------------------


def main_worktree_root(candidate) -> Path:
    """``candidate`` から main worktree の root を決定論的に導出する。

    ``karte/paths.py`` の :func:`main_worktree_root`（K-01）と同等の導出を、選択肢 LG-1
    案A に従って本モジュール内に独立実装したもの（モジュール docstring 参照）。

    判定は ``candidate/.git`` の種別で行う:
      * **ディレクトリ**なら main worktree そのもの＝``candidate`` を返す。
      * **ファイル**なら linked worktree の目印。中身の ``gitdir: <path>`` を辿り、
        ``<gitdir>/commondir`` が指す共有 ``.git`` の親を main worktree root とする。
        ``commondir`` が無い簡易環境では標準レイアウト ``<main>/.git/worktrees/<name>`` の
        ``.git`` セグメントから同じ結果を導出する。
      * ``.git`` が無い（git 管理下でない裸ディレクトリ＝テスト用の一時ディレクトリ等）
        場合は ``candidate`` をそのまま返す。

    返す値は「どこを repo-root として扱うか」の**候補**にすぎない。実際の読み書きは
    :func:`ledger_dir` のガードを必ず通る（ここでガードを迂回しない）。
    """
    root = Path(candidate).resolve()
    git_path = root / ".git"
    if git_path.is_dir():
        return root
    if not git_path.is_file():
        return root

    try:
        text = git_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        raise LedgerError("LEDGER_GIT_UNREADABLE", str(git_path)) from exc
    prefix = "gitdir:"
    if not text.startswith(prefix):
        raise LedgerError("LEDGER_GIT_FILE_INVALID", str(git_path))
    gitdir = Path(text[len(prefix):].strip())
    if not gitdir.is_absolute():
        gitdir = root / gitdir
    gitdir = gitdir.resolve()

    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        common_rel = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
        return (gitdir / common_rel).resolve().parent

    parts = gitdir.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ".git":
            return Path(*parts[: index + 1]).parent
    raise LedgerError("LEDGER_MAIN_WORKTREE_UNRESOLVED", str(gitdir))


def _resolved_root(repo_root) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise LedgerError("LEDGER_REPO_ROOT_INVALID", str(root))
    return root


def ledger_dir(repo_root, *, create: bool = False) -> Path:
    """``<repo-root>/tmp/_worktree`` を返す（``create`` で不在時に作成）。

    ``tmp`` / ``_worktree`` のいずれかが symlink なら拒否する（symlink 越しに
    リポジトリ外へ誘導された書込を許さない＝``dsv2/cleantmp.py`` と同じ様式）。
    """
    root = _resolved_root(repo_root)
    tmp = root / TMP_DIRNAME
    if tmp.is_symlink():
        raise LedgerError("LEDGER_TMP_SYMLINK", str(tmp))
    if not tmp.exists():
        if not create:
            return tmp / LEDGER_DIRNAME
        tmp.mkdir(parents=True)
    if not tmp.is_dir():
        raise LedgerError("LEDGER_TMP_NOT_DIR", str(tmp))

    target = tmp / LEDGER_DIRNAME
    if target.is_symlink():
        raise LedgerError("LEDGER_DIR_SYMLINK", str(target))
    if not target.exists():
        if not create:
            return target
        target.mkdir(parents=True)
    if not target.is_dir():
        raise LedgerError("LEDGER_DIR_NOT_DIR", str(target))
    return target


def ledger_path(repo_root, *, create_dir: bool = False) -> Path:
    """``<repo-root>/tmp/_worktree/ledger.json`` を返す（実在は要求しない）。"""
    directory = ledger_dir(repo_root, create=create_dir)
    path = directory / LEDGER_FILENAME
    if path.is_symlink():
        raise LedgerError("LEDGER_FILE_SYMLINK", str(path))
    return path


# --- 読み書き ------------------------------------------------------------------


def _initial() -> dict:
    return {"schema_version": SCHEMA_VERSION, "entries": []}


def _validate_document(value: Any, source: str) -> dict:
    if not isinstance(value, dict):
        raise LedgerError("LEDGER_CORRUPT", f"{source}: not an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise LedgerError(
            "LEDGER_SCHEMA_MISMATCH",
            f"{source}: expected {SCHEMA_VERSION}; actual {value.get('schema_version')!r}",
        )
    entries = value.get("entries")
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise LedgerError("LEDGER_CORRUPT", f"{source}: entries is not a list of objects")
    return value


def read_ledger(repo_root) -> dict:
    """台帳を読む。

    * **未作成**（``tmp/`` ごと無い場合も含む）→ ``{"schema_version": …, "entries": []}``。
      これは運用上の**正常な初期状態**であってエラーではない。
    * **壊れている**（JSON 不正・``schema_version`` 不一致・``entries`` が list でない）
      → :class:`LedgerError`（fail-close）。壊れた台帳を「無い」と同じに潰すと、
      残留の記録を失ったまま新しい dispatch を起票してしまう。
    """
    path = ledger_path(repo_root)
    if not path.exists():
        return _initial()
    if not path.is_file():
        raise LedgerError("LEDGER_NOT_A_FILE", str(path))
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerError("LEDGER_UNREADABLE", str(path)) from exc
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LedgerError("LEDGER_INVALID_JSON", str(path)) from exc
    return _validate_document(value, str(path))


def _acquire_lock(
    directory: Path, *, lock_timeout_s: float, sleep: Callable[[float], None]
) -> int:
    lock_path = directory / LEDGER_LOCK_FILENAME
    attempts = max(1, int(lock_timeout_s / LOCK_RETRY_INTERVAL_S))
    for index in range(attempts):
        try:
            return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if index == attempts - 1:
                break
            sleep(LOCK_RETRY_INTERVAL_S)
        except OSError as exc:
            raise LedgerError("LEDGER_LOCK_ERROR", str(lock_path)) from exc
    raise LedgerError(
        "LEDGER_LOCK_TIMEOUT",
        f"{lock_path}（別プロセスが保持中。残留していれば手で削除する）",
    )


def _write_atomic(path: Path, document: Mapping[str, Any]) -> None:
    tmp_path = path.with_name(LEDGER_TMP_FILENAME)
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    try:
        fd = os.open(str(tmp_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise LedgerError("LEDGER_TMP_EXISTS", str(tmp_path)) from exc
    except OSError as exc:
        raise LedgerError("LEDGER_WRITE_ERROR", str(tmp_path)) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(str(tmp_path), str(path))
    except OSError as exc:
        try:
            os.unlink(str(tmp_path))
        except OSError:
            pass
        raise LedgerError("LEDGER_WRITE_ERROR", str(path)) from exc


def update_ledger(
    repo_root,
    mutate: Callable[[dict], None],
    *,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """ロックを取り、読み → ``mutate`` → 原子的に置換する。

    ``mutate`` は台帳 document をその場で書き換える（戻り値は見ない）。
    ``mutate`` が例外を投げたら**一切書かずに**ロックを解放して送出しなおす（fail-close）。

    ロックは同一ディレクトリの ``ledger.json.lock`` を ``O_CREAT|O_EXCL`` で取る。
    取れなければ ``LOCK_RETRY_INTERVAL_S`` 刻みで固定回数リトライし、尽きたら
    ``LEDGER_LOCK_TIMEOUT``（fail-close）。**待ち時間の判定に wall clock を読まない**
    （``sleep`` を注入すればテストは実時間に依存しない）。
    """
    directory = ledger_dir(repo_root, create=True)
    path = directory / LEDGER_FILENAME
    if path.is_symlink():
        raise LedgerError("LEDGER_FILE_SYMLINK", str(path))
    lock_fd = _acquire_lock(directory, lock_timeout_s=lock_timeout_s, sleep=sleep)
    try:
        document = read_ledger(repo_root)
        mutate(document)
        _validate_document(document, "in-memory")
        _write_atomic(path, document)
        return document
    finally:
        os.close(lock_fd)
        try:
            os.unlink(str(directory / LEDGER_LOCK_FILENAME))
        except OSError:
            pass


# --- エントリ操作 --------------------------------------------------------------


def _stamp(now) -> str:
    if not isinstance(now, datetime):
        raise LedgerError("LEDGER_NOW_REQUIRED", type(now).__name__)
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_entry_id(existing: set) -> str:
    for _attempt in range(64):
        candidate = "wl-" + uuid.uuid4().hex[:12]
        if candidate not in existing:
            return candidate
    raise LedgerError("LEDGER_ENTRY_ID_EXHAUSTED")


def _validate_agent_type(value: str) -> str:
    if not isinstance(value, str) or not AGENT_TYPE_RE.fullmatch(value):
        raise LedgerError("LEDGER_AGENT_TYPE_INVALID", repr(value))
    return value


def _validate_worktree_path(value: str) -> str:
    if not isinstance(value, str) or not WORKTREE_PATH_RE.fullmatch(value):
        raise LedgerError("LEDGER_WORKTREE_PATH_INVALID", repr(value))
    return value


def open_entry(
    repo_root,
    *,
    issue: int,
    agent_type: str,
    round: int | None,
    branch_name: str | None,
    handoff_path: str | None,
    now: datetime,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """受理された dispatch を ``open`` エントリとして起票し ``entry_id`` を返す。

    ``now`` は**必須**（モジュール docstring の時刻方針）。``dispatched_at`` は診断用の
    スタンプであり、判定には一切使わない。

    ``round`` / ``handoff_path`` は現行の ``ISSUE_START_BINDING_V1`` marker schema に無いので
    本 PR では ``None`` のまま起票される（marker 拡張は PR-4）。
    """
    stamp = _stamp(now)
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise LedgerError("LEDGER_ISSUE_INVALID", repr(issue))
    _validate_agent_type(agent_type)
    if round is not None and (not isinstance(round, int) or isinstance(round, bool) or round < 1):
        raise LedgerError("LEDGER_ROUND_INVALID", repr(round))
    if branch_name is not None and not isinstance(branch_name, str):
        raise LedgerError("LEDGER_BRANCH_INVALID", repr(branch_name))
    if handoff_path is not None and not isinstance(handoff_path, str):
        raise LedgerError("LEDGER_HANDOFF_PATH_INVALID", repr(handoff_path))

    created: dict = {}

    def mutate(document: dict) -> None:
        existing = {item.get("entry_id") for item in document["entries"]}
        entry = {
            "entry_id": _new_entry_id(existing),
            "issue": issue,
            "agent_type": agent_type,
            "round": round,
            "branch_name": branch_name,
            "handoff_path": handoff_path,
            "dispatched_at": stamp,
            "agent_id": None,
            "worktree_path": None,
            "status": "open",
            "collected_to": None,
            "closed_at": None,
            "notes": [],
        }
        document["entries"].append(entry)
        created["entry_id"] = entry["entry_id"]

    update_ledger(repo_root, mutate, lock_timeout_s=lock_timeout_s, sleep=sleep)
    return created["entry_id"]


def _latest(entries, predicate) -> dict | None:
    """条件に合う**最後の**エントリ（起票順が新しいもの）を返す。"""
    for entry in reversed(entries):
        if predicate(entry):
            return entry
    return None


def latest_open_entry(repo_root, agent_type: str) -> dict | None:
    """同じ ``agent_type`` の最新の Claude ``open`` エントリ（無ければ ``None``）。

    Codex は spawn 前に workspace が確定しており :mod:`issue_start.codex_binding` が task key
    で直接束縛する。ここへ混ぜると Claude ``SubagentStart`` が Codex entry を横取りするため、
    platform 欠如（既存 entry）または ``claude`` だけを対象にする。
    """
    entries = read_ledger(repo_root)["entries"]
    return _latest(
        entries,
        lambda item: item.get("status") == "open"
        and item.get("agent_type") == agent_type
        and item.get("platform", "claude") == "claude",
    )


def bind_agent(
    repo_root,
    *,
    agent_type: str,
    agent_id: str,
    worktree_path: str,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """``agent_id`` / ``worktree_path`` を同 ``agent_type`` の最新 ``open`` エントリへ束縛する。

    束縛できたら ``entry_id``、**該当する ``open`` エントリが無ければ ``None``**（推測して
    別のエントリへ結び付けない）。

    冪等: 既に同じ ``agent_id`` で ``running`` になっているエントリがあれば、そのまま
    その ``entry_id`` を返して何も書き換えない（``SubagentStart`` の二重発火に耐える）。
    """
    _validate_agent_type(agent_type)
    if not isinstance(agent_id, str) or not AGENT_ID_RE.fullmatch(agent_id):
        raise LedgerError("LEDGER_AGENT_ID_INVALID", repr(agent_id))
    _validate_worktree_path(worktree_path)

    bound: dict = {}

    def mutate(document: dict) -> None:
        entries = document["entries"]
        already = _latest(
            entries,
            lambda item: item.get("agent_id") == agent_id
            and item.get("worktree_path") == worktree_path
            and item.get("status") == "running",
        )
        if already is not None:
            bound["entry_id"] = already["entry_id"]
            return
        target = _latest(
            entries,
            lambda item: item.get("status") == "open"
            and item.get("agent_type") == agent_type
            and item.get("platform", "claude") == "claude",
        )
        if target is None:
            bound["entry_id"] = None
            return
        target["agent_id"] = agent_id
        target["worktree_path"] = worktree_path
        target["status"] = "running"
        bound["entry_id"] = target["entry_id"]

    update_ledger(repo_root, mutate, lock_timeout_s=lock_timeout_s, sleep=sleep)
    return bound["entry_id"]


def _find(entries, entry_id: str) -> dict | None:
    for entry in entries:
        if entry.get("entry_id") == entry_id:
            return entry
    return None


def mark(
    repo_root,
    entry_id: str,
    status: str,
    *,
    now: datetime,
    note: str = "",
    collected_to: str | None = None,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """エントリの状態を遷移させる。

    逆行遷移（``released`` → ``running`` 等）は ``LEDGER_ILLEGAL_TRANSITION`` で拒否する。
    ``note`` を渡すと ``notes`` に ``{"at": <stamp>, "note": <text>}`` を1件追記する
    （**既存の notes は消さない**）。``closed_at`` は終端状態へ入ったときだけ記録する。

    **同一 status への遷移（``running`` → ``running`` 等）は許可されるが no-op ではない**
    ——``status`` の値こそ変わらないものの、終端状態なら ``closed_at`` を新しいスタンプで
    上書きし、``note`` / ``collected_to`` を渡していればそれも反映する（F-309-08：
    「同一 status は no-op＝冪等」と書いていた旧記述を実装に合わせて訂正）。
    ``closed_at`` の上書きは**意図的**——「最後にその状態を確認した時刻」が診断で要る。
    判定入力（``status``）は変わらないので、再実行が状態機械を進めることはない。
    """
    stamp = _stamp(now)
    if status not in STATUSES:
        raise LedgerError("LEDGER_STATUS_UNKNOWN", repr(status))
    if collected_to is not None and not isinstance(collected_to, str):
        raise LedgerError("LEDGER_COLLECTED_TO_INVALID", repr(collected_to))

    def mutate(document: dict) -> None:
        entry = _find(document["entries"], entry_id)
        if entry is None:
            raise LedgerError("LEDGER_ENTRY_NOT_FOUND", entry_id)
        current = entry.get("status")
        if current not in _TRANSITIONS:
            raise LedgerError("LEDGER_STATUS_UNKNOWN", f"{entry_id}: {current!r}")
        if status not in _TRANSITIONS[current]:
            raise LedgerError(
                "LEDGER_ILLEGAL_TRANSITION", f"{entry_id}: {current} -> {status}"
            )
        entry["status"] = status
        if collected_to is not None:
            entry["collected_to"] = collected_to
        if status in TERMINAL_STATUSES:
            entry["closed_at"] = stamp
        if note:
            entry.setdefault("notes", []).append({"at": stamp, "note": note})

    update_ledger(repo_root, mutate, lock_timeout_s=lock_timeout_s, sleep=sleep)


def add_note(
    repo_root,
    entry_id: str,
    *,
    now: datetime,
    note: str,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """状態を変えずに ``notes`` へ1行足す（束縛できなかった理由の記録等）。"""
    stamp = _stamp(now)
    if not note:
        raise LedgerError("LEDGER_NOTE_EMPTY", entry_id)

    def mutate(document: dict) -> None:
        entry = _find(document["entries"], entry_id)
        if entry is None:
            raise LedgerError("LEDGER_ENTRY_NOT_FOUND", entry_id)
        entry.setdefault("notes", []).append({"at": stamp, "note": note})

    update_ledger(repo_root, mutate, lock_timeout_s=lock_timeout_s, sleep=sleep)


def find_by_agent_id(repo_root, agent_id: str) -> dict | None:
    """``agent_id`` に束縛されている最新のエントリ（無ければ ``None``）。"""
    entries = read_ledger(repo_root)["entries"]
    return _latest(entries, lambda item: item.get("agent_id") == agent_id)


def unreleased_entries(repo_root) -> list:
    """``open`` / ``running`` / ``stopped`` / ``collected`` / ``stale`` のエントリ。"""
    entries = read_ledger(repo_root)["entries"]
    return [item for item in entries if item.get("status") in UNRELEASED_STATUSES]


# --- ディスク上の worktree との突き合わせ ----------------------------------------


def on_disk_worktrees(repo_root) -> list:
    """``.claude/worktrees/agent-<id>`` の形で**実在するディレクトリ**の repo-root 相対パス。

    ``agent-`` で始まらない名前・ファイル・symlink は拾わない（symlink 越しに repo 外の
    ディレクトリを台帳へ持ち込ませない）。返す形は必ず
    ``.claude/worktrees/agent-<id>``（POSIX 区切り）。
    """
    root = _resolved_root(repo_root)
    base = root / ".claude" / "worktrees"
    if base.is_symlink() or not base.is_dir():
        return []
    found = []
    for child in sorted(base.iterdir(), key=lambda item: item.name):
        if child.is_symlink() or not child.is_dir():
            continue
        if not AGENT_DIR_RE.fullmatch(child.name):
            continue
        found.append(f"{WORKTREE_ROOT_REL}/{child.name}")
    return found


def resolve_worktree_for_agent(repo_root, *, agent_id: str | None) -> tuple:
    """``SubagentStart`` の payload から worktree を決める（選択肢 BIND-1 案A）。

    返り値は ``(worktree_path | None, how)``。``how`` は判定根拠の識別子で、
    evidence（stderr）に載せるためだけに使う。

    1. **``agent_id`` 直接一致**: ``.claude/worktrees/agent-<agent_id>`` が実在すれば
       それを使う（``how="agent_id"``）。要実測事項 V-1 が「一致する」だった場合の経路。
    2. **差分検出**（``how="diff"`` ・案A の本体）: ``running`` エントリが1件も無い
       （＝live な dispatch が他に居ない）状態で、ディスク上の ``agent-*`` が
       **ちょうど1つ**なら、それが今まさに起動した dispatch のものだと決まる。
       ``/issue-pipeline`` ②の「1件ずつ直列」原則の下では一意に定まる。
    3. それ以外は ``None`` を返して**推測しない**（``how`` は
       ``"ambiguous-running"`` / ``"no-unique-candidate"`` / ``"no-worktree"``）。

    payload の内部形式（``agent_id`` の綴り・値の意味）に依存しない＝**V-1 の結果が
    どちらでも「推測で別 dispatch のエントリを潰す」ことは起きない**、が保証の範囲。

    **束縛が毎回成立するとは限らない**（F-309-03・PR 本文の旧記述を訂正）:

    * V-1 が「一致する」なら経路 1 で毎回束縛できる。
    * V-1 が「一致しない」場合、経路 2 は「``running`` が1件も無い」ことを要求する。
      したがって ``running`` を確実に retire できることが差分検出の前提になる。
      **Issue #354（PR-3）でこの前提が満たされた**——``SubagentStop`` の解放段が
      ``running`` → ``stopped`` → ``collected`` → ``released`` と進め、進められなかった
      ものは :func:`sweep_orphans` か gate の deny が拾う。PR-1 時点では
      ``running`` から抜ける出荷経路が無く「差分検出で束縛できるのは事実上初回の1件だけ」
      だったが、その制約は解消済み。
    * それでも retire に失敗した ``running`` が残っている間は ``ambiguous-running`` に
      なり、その dispatch は束縛されないまま ``open`` に ``notes`` が積まれる（推測して
      別 dispatch のエントリを潰すよりは束縛しない方を選ぶ、という PR-1 の判断は不変）。
    """
    on_disk = on_disk_worktrees(repo_root)
    if agent_id and AGENT_ID_RE.fullmatch(agent_id):
        direct = f"{WORKTREE_ROOT_REL}/agent-{agent_id}"
        if direct in on_disk:
            return direct, "agent_id"
    if not on_disk:
        return None, "no-worktree"
    entries = read_ledger(repo_root)["entries"]
    running = {
        item.get("worktree_path")
        for item in entries
        if item.get("status") == "running" and item.get("worktree_path")
    }
    if running:
        return None, "ambiguous-running"
    if len(on_disk) == 1:
        return on_disk[0], "diff"
    return None, "no-unique-candidate"


# 「回収が完了していない」＝ residue として deny の材料にする状態（Issue #354・PR-3）。
# `stopped` を含めるのは、`SubagentStop` が所有者の停止を記録したのに回収段まで到達して
# いない（＝回収が失敗した／実行されなかった）ことを意味するため。
RESIDUE_STATUSES = ("stale", "stopped", "collected")
# 「今このディスク上の worktree を正当に占有している」状態。`stopped` を含めるのは、
# 停止直後〜回収完了までの短い遷移区間でも worktree の占有は正当だから——ここから漏らすと
# 回収処理中の worktree を `ISSUE_START_WORKTREE_UNCLAIMED` として誤検出する。
CLAIMED_STATUSES = ("running", "stopped")


def _paths_with_status(entries, statuses) -> set:
    return {
        item.get("worktree_path")
        for item in entries
        if item.get("status") in statuses and item.get("worktree_path")
    }


def residue_report(repo_root) -> dict:
    """残留状態の evidence を組み立てる（deny 判定の材料＝:mod:`issue_start.gate`）。

    * ``stale``: 回収/解放が完了していないエントリ（:data:`RESIDUE_STATUSES`）。
      ``collected`` を含めるのは「回収は済んだが解放されていない＝乗っ取りの的」だから。
      ``stopped`` を含めるのは「所有者は停止したが回収がまだ＝同じく残留」だから。
    * ``unclaimed``: ディスク上に在るのに :data:`CLAIMED_STATUSES` のどのエントリにも
      紐づかない worktree。
    * ``running`` / ``stopped`` / ``claimed``: 現在正当に占有されている worktree のパス集合
      （``claimed`` は前2者の和＝``unclaimed`` の補集合の材料）。

    **``stopped`` は2つの集合に同時に現れる**（``stale`` にも ``claimed`` にも）。これは矛盾
    ではなく ``stopped`` が持つ二重の性質そのものである——「回収がまだ済んでいない」（＝
    residue として deny し、主文脈に ``collect-worktree`` を促すべき）と「今まさに回収処理中で
    worktree の占有は正当」（＝孤児として ``--force-uncollected`` 掃除を促してはならない）。
    片方だけを反映すると、それぞれ「残留に気づけない」／「回収中の worktree を孤児と誤診する」
    という別々の失敗になる。
    """
    entries = read_ledger(repo_root)["entries"]
    running = _paths_with_status(entries, ("running",))
    stopped = _paths_with_status(entries, ("stopped",))
    claimed = running | stopped
    on_disk = set(on_disk_worktrees(repo_root))
    return {
        "stale": [item for item in entries if item.get("status") in RESIDUE_STATUSES],
        "unclaimed": sorted(on_disk - claimed),
        "running": sorted(running),
        "stopped": sorted(stopped),
        "claimed": sorted(claimed),
    }


def sweep_orphans(
    repo_root,
    *,
    now: datetime,
    lock_timeout_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list:
    """占有を主張しているのに worktree が実在しないエントリを ``stale`` へ落とす。

    対象は :data:`CLAIMED_STATUSES`（``running`` / ``stopped``）で ``worktree_path`` を持ち、
    **その worktree がディスク上に無い**エントリ。これらは「所有者も実体も居ないのに占有を
    主張し続ける」状態で、放置すると
      * ``running`` は :func:`resolve_worktree_for_agent` の差分検出を恒久的に
        ``ambiguous-running`` にして以後の束縛を全部潰す、
      * ``claimed`` 集合に居座って本物の孤児 worktree の ``unclaimed`` 検出を鈍らせる、
    という2つの害を出す。``stale`` へ落とせば gate が
    ``ISSUE_START_WORKTREE_RESIDUE`` で deny し、主文脈が明示的に片付けることになる。

    **判定入力は状態と実在だけで、時刻を一切読まない**（``now`` は notes のスタンプ専用）。
    ``open`` を対象に含めない理由はモジュール docstring の状態遷移図の注記を見る。

    **落とす候補が1件も無ければ台帳へ書き込まない**（ロックも取らない）。正常系で毎 dispatch
    ごとに台帳ファイルを触らないため、掃引が新たな失敗要因にならない。

    返り値は ``stale`` へ落とした ``entry_id`` のリスト（起票順）。
    """
    entries = read_ledger(repo_root)["entries"]
    on_disk = set(on_disk_worktrees(repo_root))
    orphans = [
        item["entry_id"]
        for item in entries
        if item.get("status") in CLAIMED_STATUSES
        and item.get("platform", "claude") == "claude"
        and item.get("worktree_path")
        and item.get("worktree_path") not in on_disk
        and isinstance(item.get("entry_id"), str)
    ]
    if not orphans:
        return []
    stamp = _stamp(now)
    targets = set(orphans)

    def mutate(document: dict) -> None:
        for entry in document["entries"]:
            if entry.get("entry_id") not in targets:
                continue
            # 掃引と書込の間に状態が進んでいたら触らない（読み→書きの間の競合を素通しさせない）。
            if entry.get("status") not in CLAIMED_STATUSES:
                targets.discard(entry.get("entry_id"))
                continue
            entry["status"] = "stale"
            entry.setdefault("notes", []).append({
                "at": stamp,
                "note": (
                    "sweep-orphans: 占有を主張しているが worktree が実在しないため stale へ落とした"
                    f"（{entry.get('worktree_path')}）"
                ),
            })

    update_ledger(repo_root, mutate, lock_timeout_s=lock_timeout_s, sleep=sleep)
    return [entry_id for entry_id in orphans if entry_id in targets]
