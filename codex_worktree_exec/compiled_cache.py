"""未追跡cacheをHEADの通常sourceから生成したcode bytesへ読取束縛する。"""
import importlib.util
import marshal
import sys
from pathlib import Path
from feedback_ledger.paths import FeedbackPathError
from issue_envelope.path_binding import committed_bytes


def verify_compiled_cache(cache: Path, worktree: Path, *, source_bytes=None) -> None:
    """cacheのcodeをdecode/実行せず、標準compilerの出力と比較する。"""
    root, cache = worktree.resolve(), cache.absolute()
    if (not cache.is_relative_to(root) or not cache.is_file()
            or any(path.is_symlink() for path in (cache, *cache.parents))):
        raise ValueError("compiled cache is not a regular in-worktree file")
    source = Path(importlib.util.source_from_cache(str(cache)))
    if (not source.is_relative_to(root) or not source.is_file()
            or any(path.is_symlink() for path in (source, *source.parents))):
        raise ValueError("compiled cache source is not a regular in-worktree file")
    if source_bytes is None:
        source_bytes = {}
    if source not in source_bytes:
        try:
            source_bytes[source] = committed_bytes(root, source.relative_to(root).as_posix())
        except FeedbackPathError as error:
            raise ValueError("compiled cache source path is unsafe") from error
    content = source_bytes[source]
    if source.read_bytes() != content:
        raise ValueError("compiled cache source changed during validation")
    levels = [level for level in range(3) if cache == Path(importlib.util.cache_from_source(
        str(source), optimization="" if level == 0 else str(level)))]
    if len(levels) != 1:
        raise ValueError("compiled cache tag/optimization is not supported")
    raw = cache.read_bytes()
    if (len(raw) < 16 or raw[:4] != importlib.util.MAGIC_NUMBER
            or int.from_bytes(raw[4:8], "little") not in (0, 1, 3)):
        raise ValueError("compiled cache header is not supported")
    relative = source.relative_to(root).as_posix()
    for filename in (str(source), relative, "./" + relative):
        for interned in (False, True):
            name = filename.encode().decode()
            if interned:
                name = sys.intern(name)
            try:
                expected = compile(content, name, "exec", dont_inherit=True, optimize=levels[0])
            except (SyntaxError, OverflowError) as error:
                raise ValueError("compiled cache source cannot be compiled") from error
            if raw[16:] == marshal.dumps(expected):
                return
    raise ValueError("compiled cache does not match committed source; regenerate from trusted source")
