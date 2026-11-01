"""WSL入力pathをnative起動の明示入力表現へ射影する。OS cwd観測とは区別。"""

import hashlib
import json
import os
import pwd
import re
import sys
from pathlib import Path


def digest_value(value: object) -> str:
    """bindingの複合値を曖昧な文字列連結でなくcanonical JSONへ固定する。"""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def text_sha256(value: str) -> str:
    """workspace indexと同じ、UTF-8文字列そのもののfingerprint。"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def native_workspace_path(path: Path) -> str:
    """実効相対解決は別途witnessで確かめ、ここではcaller入力だけを表現する。"""
    distribution = os.environ.get("WSL_DISTRO_NAME", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", distribution) or not path.is_absolute():
        raise ValueError("cohort_native_projection_unsupported")
    canonical = path.resolve(strict=True)
    if "\\" in str(canonical):
        raise ValueError("cohort_native_projection_unsupported")
    return "//wsl.localhost/" + distribution + canonical.as_posix()


def native_executable_path(canonical: Path) -> str:
    """既に検査したcanonical exe入力をWin32表現へ射影する。存在認定ではない。"""
    if not canonical.is_absolute() or ".." in canonical.parts:
        raise ValueError("cohort_native_projection_unsupported")
    parts = canonical.parts
    if len(parts) > 3 and parts[1] == "mnt" and re.fullmatch(r"[A-Za-z]", parts[2]):
        return parts[2].upper() + ":\\" + "\\".join(parts[3:])
    return native_workspace_path(canonical)


def wsl_user_binding(windows_principal_sha256: str) -> str:
    """実UID homeを使い、HOME/XDGやaccountの自己申告をidentityにしない。"""
    return digest_value({"uid": os.getuid(), "home": pwd.getpwuid(os.getuid()).pw_dir,
                         "windows_principal_sha256": windows_principal_sha256})


def os_binding(windows_os_sha256: str) -> str:
    """PS provider cwd等は含めず、実行OSとPython ABIと入力distributionを束縛。"""
    return digest_value({"wsl_release": os.uname().release,
                         "distribution": os.environ.get("WSL_DISTRO_NAME", ""),
                         "python": list(sys.version_info[:2]), "windows_os_sha256": windows_os_sha256})
