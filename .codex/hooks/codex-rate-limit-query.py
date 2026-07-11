#!/usr/bin/env python3
"""Query Codex's structured rate-limit API (Issue #195).

Replaces tmux pane text scraping as the *primary* rate-limit signal for the
Codex Stop hook / watcher. Instead of regex-matching a rendered banner, this
drives ``codex app-server --stdio`` over JSON-RPC and calls the
``account/rateLimits/read`` method, which returns machine-readable data:

    rateLimits.primary   / .secondary : { usedPercent, windowDurationMins, resetsAt }
    rateLimits.rateLimitReachedType   : null == not limited, else an enum value
    rateLimits.planType

(Response shape verified live against ``codex-cli`` 0.144.1 —
``codex app-server generate-json-schema`` /
``v2/GetAccountRateLimitsResponse.json``. The method itself is listed in
``ClientRequest.json`` as ``account/rateLimits/read`` with ``params: null``.)

The bash hooks call this helper and read back simple ``RL_*=value`` lines:

    RL_OK=1              query succeeded (always printed on success)
    RL_REACHED=0|1       rateLimitReachedType is non-null
    RL_REACHED_TYPE=...  the enum value (empty when not reached)
    RL_RESET_EPOCH=...   Unix seconds to wait until (binding window's resetsAt)
    RL_WINDOW_MINS=...   binding window duration; lets bash skip weekly limits
    RL_USED_PERCENT=...  binding window usedPercent (or max window when idle)
    RL_PLAN=...          planType

Exit codes: 0 == query succeeded (RL_OK=1 printed); non-zero == the API was
unavailable / errored / timed out (RL_OK=0 printed, reason on stderr). The
non-zero path is what tells the bash caller to fall back to the legacy text
parser.

`依存仕様:` Codex app-server protocol v2 method ``account/rateLimits/read`` and
``GetAccountRateLimitsResponse`` (``codex-cli`` 0.144.1). No in-graph SPEC node
covers this external protocol yet; the format anchor is the schema emitted by
``codex app-server generate-json-schema`` for the installed release. Kept
standard-library only per this repo's Q5 tooling constraint.
"""

import argparse
import json
import os
import subprocess
import sys
import time


def _windows(snapshot):
    """Yield (name, window_dict) for the present primary/secondary windows."""
    for name in ("primary", "secondary"):
        win = snapshot.get(name)
        if isinstance(win, dict):
            yield name, win


def pick_binding_window(snapshot, now):
    """Choose the window whose reset gates recovery.

    When a limit is reached, recovery must wait for every *exhausted* window to
    reset, so the binding window is the exhausted one that resets latest. When
    nothing is exhausted (idle / informational call), fall back to the window
    with the highest usage that still has a future reset time, so callers can
    surface a meaningful used-percent/reset even when not limited.
    """
    exhausted = [
        win
        for _, win in _windows(snapshot)
        if isinstance(win.get("usedPercent"), (int, float))
        and win["usedPercent"] >= 100
        and isinstance(win.get("resetsAt"), (int, float))
    ]
    if exhausted:
        return max(exhausted, key=lambda w: w["resetsAt"])

    future = [
        win
        for _, win in _windows(snapshot)
        if isinstance(win.get("resetsAt"), (int, float))
        and win["resetsAt"] > now - 60
    ]
    if future:
        return max(future, key=lambda w: w.get("usedPercent") or 0)
    return None


def summarize_rate_limits(response, now):
    """Turn a raw ``account/rateLimits/read`` result into normalized fields.

    Pure function (no I/O) so it can be unit-tested against captured/synthetic
    responses. ``response`` is the JSON-RPC ``result`` object, i.e. it has a
    top-level ``rateLimits`` snapshot.
    """
    snapshot = response.get("rateLimits")
    if not isinstance(snapshot, dict):
        raise ValueError("response has no rateLimits snapshot")

    reached_type = snapshot.get("rateLimitReachedType")
    reached = reached_type is not None

    binding = pick_binding_window(snapshot, now)
    reset_epoch = ""
    window_mins = ""
    used_percent = ""
    if binding is not None:
        if isinstance(binding.get("resetsAt"), (int, float)):
            reset_epoch = int(binding["resetsAt"])
        if isinstance(binding.get("windowDurationMins"), (int, float)):
            window_mins = int(binding["windowDurationMins"])
        if isinstance(binding.get("usedPercent"), (int, float)):
            used_percent = int(binding["usedPercent"])

    return {
        "RL_OK": 1,
        "RL_REACHED": 1 if reached else 0,
        "RL_REACHED_TYPE": reached_type if isinstance(reached_type, str) else "",
        "RL_RESET_EPOCH": reset_epoch,
        "RL_WINDOW_MINS": window_mins,
        "RL_USED_PERCENT": used_percent,
        "RL_PLAN": snapshot.get("planType") or "",
    }


def _emit(fields):
    for key, value in fields.items():
        sys.stdout.write("%s=%s\n" % (key, value))


def call_app_server(cmd, timeout):
    """Drive ``codex app-server --stdio`` and return the rateLimits result dict.

    Sends ``initialize`` -> ``initialized`` -> ``account/rateLimits/read`` and
    returns the ``result`` object of the read response. Raises on any
    failure/timeout so ``main`` can report RL_OK=0.
    """
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # stdin/stdout are typed as IO[str] | None by subprocess.Popen, but the
    # PIPE args above guarantee they are non-None here. Assert and bind to
    # local names so Pyright narrows the type for reportOptionalMemberAccess
    # (narrowing from a bare `proc.stdin`/`proc.stdout` assert does not
    # propagate into the nested `send` closure below; see PR #196's
    # type-clean policy).
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc_stdin = proc.stdin
    proc_stdout = proc.stdout

    def send(obj):
        proc_stdin.write(json.dumps(obj) + "\n")
        proc_stdin.flush()

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "codex-rate-limit-hook",
                        "version": "1.0.0",
                    }
                },
            }
        )
        send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "account/rateLimits/read",
                "params": None,
            }
        )
        # Deliberately keep stdin OPEN until we have the reply: the installed
        # app-server (0.144.x) shuts the connection down when stdin closes, and
        # will otherwise race the read response and time us out.

        deadline = time.time() + timeout
        while time.time() < deadline:
            line = proc_stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            # Notifications carry "method" but no "id"; skip them.
            if msg.get("id") != 2:
                continue
            if "error" in msg:
                raise RuntimeError("app-server error: %s" % msg["error"])
            result = msg.get("result")
            if not isinstance(result, dict):
                raise RuntimeError("read response has no result object")
            return result
        raise TimeoutError("no rateLimits response within %ss" % timeout)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("CODEX_RL_API_TIMEOUT", "12")),
        help="seconds to wait for the rateLimits response",
    )
    parser.add_argument(
        "--codex-cmd",
        default=os.environ.get("CODEX_RL_APP_SERVER_CMD", "codex app-server --stdio"),
        help="command used to launch the app-server (shell-split)",
    )
    args = parser.parse_args(argv)

    cmd = args.codex_cmd.split()
    if not cmd:
        sys.stderr.write("empty --codex-cmd\n")
        _emit({"RL_OK": 0})
        return 2

    try:
        result = call_app_server(cmd, args.timeout)
        fields = summarize_rate_limits(result, int(time.time()))
    except FileNotFoundError:
        sys.stderr.write("codex binary not found (%s)\n" % cmd[0])
        _emit({"RL_OK": 0})
        return 2
    except Exception as exc:  # noqa: BLE001 - any failure => fall back to text
        sys.stderr.write("rate-limit API query failed: %s\n" % exc)
        _emit({"RL_OK": 0})
        return 2

    _emit(fields)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
