"""Project pull request repository identifiers and Actions associations."""

def _positive(value):
    return value if type(value) is int and value > 0 else None


def pull_identity(row, normalize_oid):
    base = row["base"]
    repository = base.get("repo")
    head = row.get("head")
    repository_name = repository.get("full_name") if isinstance(repository, dict) else None
    ref = base.get("ref")
    return {
        "id": _positive(row.get("id")),
        "base": ref if isinstance(ref, str) and ref else None,
        "base_repo_id": _positive(repository.get("id")) if isinstance(repository, dict) else None,
        "base_repository": repository_name.lower() if isinstance(repository_name, str) else None,
        "base_sha": normalize_oid(base.get("sha")),
        "head_sha": normalize_oid(head.get("sha")) if isinstance(head, dict) else None,
        "merge_commit_sha": normalize_oid(row.get("merge_commit_sha")),
        "changed_files": _positive(row.get("changed_files")),
    }


def run_pull_requests(row, normalize_oid):
    if "pull_requests" not in row or not isinstance(row["pull_requests"], list):
        return None
    return [_run_pull(pull, normalize_oid) for pull in row["pull_requests"]]


def _run_pull(pull, normalize_oid):
    head = pull.get("head")
    base = pull.get("base")
    repository = base.get("repo") if isinstance(base, dict) else None
    return {
        "id": _positive(pull.get("id")),
        "number": _positive(pull.get("number")),
        "base_repo_id": _positive(repository.get("id")) if isinstance(repository, dict) else None,
        "head_sha": normalize_oid(head.get("sha")) if isinstance(head, dict) else None,
    }


def changed_file(row):
    filename = row["filename"]
    previous = row.get("previous_filename")
    if not isinstance(filename, str) or not filename:
        raise ValueError("changed filename must be non-empty text")
    if previous is not None and (not isinstance(previous, str) or not previous):
        raise ValueError("previous filename must be non-empty text")
    if not isinstance(row["status"], str):
        raise ValueError("file status must be text")
    return {"id": filename, "filename": filename, "previous_filename": previous, "status": row["status"]}
