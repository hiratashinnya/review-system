"""保持 directory fd の下で CreateNew/fsync/readback を順序通り実行する。"""

import os

from .cohort_private_io import private_file_bytes

CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def create_private_file(directory_fd: int, name: str, content: bytes) -> None:
    """新規 file を0600で確定し、同じ名前から bytes を readback する。"""
    descriptor = os.open(name, CREATE_FLAGS, 0o600, dir_fd=directory_fd)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    actual, _ = private_file_bytes(directory_fd, name)
    if actual != content:
        raise ValueError("cohort_publication_readback_mismatch")


def create_or_verify_proof(directory_fd: int, digest: str, encoded: bytes) -> None:
    """同hash名の既存proofはowner/mode/bytes一致時だけ再利用する。"""
    name = f"{digest}.json"
    try:
        create_private_file(directory_fd, name, encoded)
    except FileExistsError:
        content, _ = private_file_bytes(directory_fd, name, sync=True)
        if content != encoded:
            raise ValueError("cohort_existing_proof_mismatch")
    os.fsync(directory_fd)
