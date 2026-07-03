**パス**: `spec_inspector/ports.py`
**責務**: FileSystemPort 抽象 IF（Protocol）を定義する（P-1 が依存するポート）。
**公開 I/F**: `FileSystemPort`（Protocol）
**依存**: domain のみ（core / adapters / __main__ に依存しない）
**依存方向**: ports ← domain
