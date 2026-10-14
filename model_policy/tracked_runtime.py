"""無視対象 runtime が誤って Git 正本へ追加されていないことを確認する。"""

import subprocess


def check_tracked_runtime(root, runner=subprocess.run):
    completed = runner(["git", "ls-files", "--", ".github/agents/runtime-*.agent.md"],
                       cwd=root, capture_output=True, text=True, check=True, timeout=10)
    if completed.stdout.strip():
        raise ValueError("STOP: runtime agent を Git に追跡してはいけません")
