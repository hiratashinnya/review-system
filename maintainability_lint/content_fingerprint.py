"""既存負債ファイルの内容 fingerprint。"""

import hashlib


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
