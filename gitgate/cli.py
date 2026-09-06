"""gitgate の中核: verb → 固定 git argv の組み立てと実行（標準ライブラリのみ）。

`python3 -m gitgate <verb> [args]` で起動する。各 verb は厳格な引数スキーマを持ち、
想定外の引数は `GitgateError` を送出して git を一切実行しない（exec/write 面を構造的に閉じる）。

git 実行は build_git_argv() が返す list を subprocess.run([...], shell=False) に渡す。
**shell は使わない**（コマンド置換・リダイレクト・別プログラム起動が構造的に不可能）。

依存仕様: gitgate/__init__.py の docstring 参照（Issue #227 追加修正3・オーナー確定 2026-07-13）。
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from branch_source import BranchSourceError, create_branch, parse_new_branch_args

from .adopt import adopt_branch, parse_adopt_branch_args
from .worktree import (
    WorktreeError,
    collect_worktree,
    default_repo_root,
    parse_collect_worktree_args,
    parse_worktree_forget_args,
    parse_worktree_release_args,
    worktree_forget,
    worktree_release,
)


class GitgateError(Exception):
    """想定外の引数・不正な leaf 値を検知したときに送出する。git は実行されない。"""


# --- leaf 検証 --------------------------------------------------------------
# leaf 値は list 渡し（shell=False）なのでシェル解釈は起きないが、以下を追加で防ぐ:
#   - 改行 / NUL: 引数の分断・ログ汚染・想定外の複数値化を防ぐ（一律拒否）。
#   - 先頭 `-`: git がオプションとして解釈するのを防ぐ（ブランチ名・ref。パスは `--` 以降に置く）。
#   - charset: ブランチ名・ref は安全な文字集合に限定する。

BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
# ref は diff 用。`main...HEAD` `HEAD~1` `HEAD^` `origin/main` `main@` 等の一般的な指定を許容する
# 安全 charset（`{ }` 等は含めない＝過剰許可を避ける）。
REF_RE = re.compile(r"^[A-Za-z0-9._/@~^-]+$")
INTEGER_RE = re.compile(r"^[0-9]+$")


def _reject_control_chars(value, what):
    if "\n" in value or "\r" in value or "\0" in value:
        raise GitgateError(f"{what} must not contain newline or NUL characters")


def validate_path(value):
    """`git add -- <paths>` の leaf。`--` 以降に置くためオプション解釈はされない。
    改行・NUL・空文字のみ拒否する（それ以外は pathspec としてそのまま git に渡す）。"""
    if value == "":
        raise GitgateError("path argument must not be empty")
    _reject_control_chars(value, "path argument")
    return value


def validate_branch_name(value):
    _reject_control_chars(value, "branch name")
    if value.startswith("-"):
        raise GitgateError(f"branch name must not start with '-': {value!r}")
    if not BRANCH_NAME_RE.match(value):
        raise GitgateError(
            f"branch name contains disallowed characters (allowed: A-Z a-z 0-9 . _ / -): {value!r}"
        )
    return value


def validate_ref(value):
    _reject_control_chars(value, "ref")
    if value.startswith("-"):
        raise GitgateError(f"ref must not start with '-': {value!r}")
    if not REF_RE.match(value):
        raise GitgateError(
            f"ref contains disallowed characters (allowed: A-Z a-z 0-9 . _ / @ ~ ^ -): {value!r}"
        )
    return value


def validate_integer(value):
    _reject_control_chars(value, "integer")
    if not INTEGER_RE.match(value):
        raise GitgateError(f"expected a non-negative integer, got: {value!r}")
    return value


def validate_grep_pattern(value):
    # `--grep=<pat>` の単一引数としてデータ渡しする（list 渡し＝shell 解釈なし）。改行・NUL のみ拒否。
    _reject_control_chars(value, "grep pattern")
    return value


# --- verb ハンドラ ----------------------------------------------------------
# 各ハンドラは verb 引数 list を受け取り、固定テンプレートに沿った git argv（list）を返す。
# 想定外の引数は GitgateError を送出する（git は実行されない）。


def _require_no_args(verb, args):
    if args:
        raise GitgateError(f"`{verb}` takes no arguments; unexpected: {args!r}")


def verb_status(args):
    _require_no_args("status", args)
    return ["git", "status"]


def verb_add(args):
    # 全ての引数をパスとして扱い、`--` 以降に置く（オプション解釈を無効化）。最低1つ必要。
    if not args:
        raise GitgateError("`add` requires at least one path")
    paths = [validate_path(a) for a in args]
    return ["git", "add", "--", *paths]


def verb_commit(args):
    if len(args) != 1:
        raise GitgateError("`commit` requires exactly one argument: <message-file>")
    path = args[0]
    _reject_control_chars(path, "commit message file path")
    if not os.path.isfile(path):
        raise GitgateError(f"commit message file does not exist or is not a regular file: {path!r}")
    return ["git", "commit", "-F", path]


def verb_push(args):
    _require_no_args("push", args)
    return ["git", "push", "-u", "origin", "HEAD"]


def verb_branch_current(args):
    _require_no_args("branch-current", args)
    return ["git", "branch", "--show-current"]


def verb_new_branch(args):
    try:
        request = parse_new_branch_args(args)
    except BranchSourceError as exc:
        raise GitgateError(str(exc)) from exc
    # `main()` は branch_source policy を実行する。この builder の戻り値も
    # current HEAD を暗黙継承せず、検証済み exact OID を常に明示する。
    return ["git", "switch", "-c", request.branch_name, request.base_oid]


def verb_fetch(args):
    _require_no_args("fetch", args)
    return ["git", "fetch", "--prune", "origin"]


def verb_diff(args):
    # `diff [--stat] [<ref>...]` → `git diff [--stat] [<ref>...]`。
    # 受け付けるフラグは `--stat` のみ（`--output` 等の write 系フラグは一切受け付けない）。
    argv = ["git", "diff"]
    stat_seen = False
    for a in args:
        if a == "--stat":
            if not stat_seen:
                argv.append("--stat")
                stat_seen = True
            continue
        if a.startswith("-"):
            raise GitgateError(f"`diff` only accepts the `--stat` flag; unexpected flag: {a!r}")
        argv.append(validate_ref(a))
    return argv


def verb_log(args):
    # `log [-n <N>] [--grep <pat>] [--oneline]` → `git log …`。フラグは固定集合のみ、位置引数は不可。
    argv = ["git", "log"]
    i = 0
    seen = set()
    while i < len(args):
        a = args[i]
        if a == "-n":
            if i + 1 >= len(args):
                raise GitgateError("`log -n` requires an integer argument")
            n = validate_integer(args[i + 1])
            argv += ["-n", n]
            i += 2
            continue
        if a.startswith("-n") and len(a) > 2:
            # `-n5` の連結形
            n = validate_integer(a[2:])
            argv += ["-n", n]
            i += 1
            continue
        if a == "--grep":
            if i + 1 >= len(args):
                raise GitgateError("`log --grep` requires a pattern argument")
            pat = validate_grep_pattern(args[i + 1])
            argv.append("--grep=" + pat)
            i += 2
            continue
        if a.startswith("--grep="):
            pat = validate_grep_pattern(a[len("--grep="):])
            argv.append("--grep=" + pat)
            i += 1
            continue
        if a == "--oneline":
            if "--oneline" not in seen:
                argv.append("--oneline")
                seen.add("--oneline")
            i += 1
            continue
        raise GitgateError(
            f"`log` only accepts `-n <N>`, `--grep <pat>` and `--oneline`; unexpected argument: {a!r}"
        )
    return argv


VERB_HANDLERS = {
    "status": verb_status,
    "add": verb_add,
    "commit": verb_commit,
    "push": verb_push,
    "branch-current": verb_branch_current,
    "new-branch": verb_new_branch,
    "fetch": verb_fetch,
    "diff": verb_diff,
    "log": verb_log,
}


def build_git_argv(argv):
    """`argv`（verb + その引数の list）から固定テンプレートに沿った git argv を組み立てて返す。
    想定外の verb / 引数は GitgateError を送出する（副作用なし・純関数）。"""
    if not argv:
        raise GitgateError("missing verb; usage: python3 -m gitgate <verb> [args]")
    verb = argv[0]
    handler = VERB_HANDLERS.get(verb)
    if handler is None:
        allowed = ", ".join(sorted(VERB_HANDLERS))
        raise GitgateError(f"unknown verb {verb!r}; allowed verbs: {allowed}")
    return handler(argv[1:])


# --- policy 実行を伴う verb（純 argv 経路には載せない） --------------------------
# `new-branch` / `adopt-branch` / `worktree-*` は「git argv を1つ組み立てて実行する」形に
# 収まらない（fresh fetch + API 検証、台帳の状態遷移、回収→検証→解放の段構造を伴う）。
# よって `VERB_HANDLERS`（＝`build_git_argv` の純 argv ディスパッチ）には登録せず、
# `main()` 側で分岐する。`build_git_argv` にこれらを渡すと `unknown verb` になるのが正しい。
WORKTREE_VERBS = ("worktree-release", "collect-worktree", "worktree-forget")


def _now():
    """wall clock を読むのは CLI 境界だけ（`.claude/rules/04-test-data.md`）。

    `gitgate/worktree.py` は `now` を引数で受け取るだけで `datetime.now()` を呼ばない。
    """
    return datetime.now(timezone.utc)


def _run_worktree_verb(verb, args):
    """`worktree-*` verb を実行し、実施内容を stderr に1行残して 0 を返す。"""
    repo_root = default_repo_root()
    if verb == "worktree-release":
        request = parse_worktree_release_args(args)
        outcome = worktree_release(
            repo_root,
            request.worktree_path,
            entry_id=request.entry_id,
            force_uncollected=request.force_uncollected,
            reason=request.reason,
            now=_now(),
        )
        sys.stderr.write(
            f"gitgate: worktree-release {outcome.worktree_path} "
            f"entry={outcome.entry_id or '-'} removed={'yes' if outcome.removed else 'no'} "
            f"status={outcome.status}\n"
        )
        return 0
    if verb == "collect-worktree":
        request = parse_collect_worktree_args(args)
        outcome = collect_worktree(
            repo_root,
            entry_id=request.entry_id,
            worktree_path=request.worktree_path,
            handoff_path=request.handoff_path,
            into=request.into,
            allow_missing_handoff=request.allow_missing_handoff,
            reason=request.reason,
            now=_now(),
        )
        sys.stderr.write(
            f"gitgate: collect-worktree {outcome.worktree_path} "
            f"entry={outcome.entry_id or '-'} collected_to={outcome.collected_to or '-'} "
            f"released={'yes' if outcome.released else 'no'}\n"
        )
        return 0
    request = parse_worktree_forget_args(args)
    entry = worktree_forget(
        repo_root, request.entry_id, reason=request.reason, now=_now()
    )
    sys.stderr.write(
        f"gitgate: worktree-forget {request.entry_id} status={entry.get('status')} "
        "(worktree は削除していない)\n"
    )
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        if argv and argv[0] == "adopt-branch":
            request = parse_adopt_branch_args(argv[1:])
            result = adopt_branch(request)
            sys.stderr.write(
                "gitgate: adopt-branch "
                f"{result.repository}@{result.expected_oid} "
                f"pr={result.pr if result.pr is not None else '-'} "
                f"policy={result.policy_version}\n"
            )
            sys.stderr.write(
                f"gitgate: adopted existing branch '{request.branch_name}' (checkout performed)\n"
            )
            return 0
        if argv and argv[0] in WORKTREE_VERBS:
            return _run_worktree_verb(argv[0], argv[1:])
        if argv and argv[0] == "new-branch":
            request = parse_new_branch_args(argv[1:])
            result = create_branch(request)
            sys.stderr.write(
                "gitgate: new-branch source "
                f"{result.source_kind} {result.repository}@{result.source_oid} "
                f"policy={result.policy_version}\n"
            )
            sys.stderr.write(
                f"gitgate: switched to new branch '{request.branch_name}' (checkout performed)\n"
            )
            return 0
        git_argv = build_git_argv(argv)
    except BranchSourceError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    except WorktreeError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    except GitgateError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    # shell=False で list 渡し（ユーザ制御文字列はシェルに解釈されない）。
    completed = subprocess.run(git_argv, shell=False)
    return completed.returncode
