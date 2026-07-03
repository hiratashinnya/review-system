**status: decided**（2026-06-16 暫定決定・設計フェーズ）

**論点**: ファイルシステムアクセスを抽象化するポートを「list_md_files + read_file を1つにまとめる FileSystemPort」にするか「ListPort / ReadPort を別々に定義」するか。

**選択肢**:
- A: 単一 FileSystemPort（list_md_files: Path → list[Path], read_file: Path → str）
- B: ListFilesPort と ReadFilePort を別ポートとして定義

**推奨**: A（単一 Port）。理由: list と read は常にペアで使われ（list してから各ファイルを read）、別 Port にしても合成ルートの DI が複雑になるだけで利点がない。FakeFsAdapter も1つ実装すれば済む。Python の `Protocol` で2つのメソッドを持てばよい。

**決定**: A を暫定採用（2026-06-16）

**影響範囲**:
- PORT-1（FileSystemPort）は2メソッド持つ単一 Protocol として定義
- MOD-11（adapters/fs.py）は RealFsAdapter + FakeFsAdapter の2クラスを同一ファイルに置く
- 将来 write_file が必要になった場合は FileSystemPort にメソッドを追加（MINOR バンプ）するか、WritePort を別途追加する
