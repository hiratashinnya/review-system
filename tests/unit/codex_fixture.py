"""単体試験用の、実行時検査を通る偽 Codex 配布物。

本番コードの Codex 配布物検査をモックで置き換えないため、テストごとの一時ディレクトリに
launcher、同じ階層の native Codex / code-mode host、package.json を作る。launcher は
``--version`` だけを実装し、検査対象である版情報を package.json と一致させる。
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def install_fake_codex_distribution(root: Path, *, version: str = "1.0.0") -> dict[str, Path]:
    """``root/codex`` に本番と同じ配置の偽 Codex 配布物を作る。

    ``codex`` lookup は launcher の PATH 名であり、実体は package の ``bin/codex.js``
    へ解決される symlink とする。native executable と code-mode host は同じ vendor
    ``bin`` の正確な兄弟として作る。返却した ``lookup_dir`` だけを試験の PATH へ先頭注入
    することで、ホストに Codex がインストールされているかどうかに依存しない。
    """

    package_root = root / "codex"
    native_dir = (
        package_root
        / "node_modules"
        / "@openai"
        / "codex-linux-x64"
        / "vendor"
        / "x86_64-unknown-linux-musl"
        / "bin"
    )
    launcher = package_root / "bin" / "codex.js"
    native = native_dir / "codex"
    code_mode_host = native_dir / "codex-code-mode-host"
    lookup_dir = root / "fake-codex-path"

    launcher.parent.mkdir(parents=True, mode=0o755)
    native_dir.mkdir(parents=True, mode=0o755)
    lookup_dir.mkdir(mode=0o755)
    (package_root / "package.json").write_text(
        json.dumps({"name": "@openai/codex", "version": version}) + "\n",
        encoding="utf-8",
    )
    (package_root / "package.json").chmod(0o644)
    (package_root / "node_modules/@openai/codex-linux-x64/package.json").write_text(
        json.dumps({"name": "@openai/codex-linux-x64", "version": version}) + "\n",
        encoding="utf-8",
    )
    (package_root / "node_modules/@openai/codex-linux-x64/package.json").chmod(0o644)
    launcher.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"--version\" ]; then printf 'codex {version}\\n'; exit 0; fi\n"
        "printf 'fake Codex launcher accepts only --version\\n' >&2\n"
        "exit 64\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    native.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"--version\" ]; then printf 'codex {version}\\n'; exit 0; fi\n"
        "exit 64\n",
        encoding="utf-8",
    )
    native.chmod(0o755)
    code_mode_host.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"--version\" ]; then printf 'codex-code-mode-host {version}\\n'; exit 0; fi\n"
        "exit 64\n",
        encoding="utf-8",
    )
    code_mode_host.chmod(0o755)
    (lookup_dir / "codex").symlink_to(launcher)

    return {
        "package_root": package_root,
        "launcher": launcher,
        "native": native,
        "code_mode_host": code_mode_host,
        "lookup_dir": lookup_dir,
    }


def fake_codex_path_environment(lookup_dir: Path) -> str:
    """偽配布物を優先し、標準 Unix コマンドだけを残した PATH を返す。"""

    return os.pathsep.join((str(lookup_dir), "/usr/bin", "/bin"))
