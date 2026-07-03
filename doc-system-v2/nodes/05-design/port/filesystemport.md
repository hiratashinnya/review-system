```python
class FileSystemPort(Protocol):
    def list_md_files(self, root: Path) -> list[Path]: ...
    def read_file(self, path: Path) -> str: ...
```

**目的**: ファイルシステム副作用（`.md` ファイル列挙・読み出し）を抽象化し、core を実 I/O から切り離す。
**方向**: driven（外向き・副作用を抽象化）
**実装アダプタ**: RealFsAdapter（本番）/ FakeFsAdapter（テスト用シーム）
