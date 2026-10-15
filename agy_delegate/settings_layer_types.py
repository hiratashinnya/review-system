"""内部 adapter が返す層構成。CLI/設定ファイルからの自己申告入口はない。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SettingsLayer:
    name: str
    path: Path | None
    decode_permissions: Callable[[object], object] | None = None
    absent: bool = False


@dataclass(frozen=True)
class SettingsResolution:
    layers: tuple[SettingsLayer, ...] = ()
    reasons: tuple[str, ...] = ()
