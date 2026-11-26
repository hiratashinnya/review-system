"""Acquire the evidence for one collection, shared by all requested periods."""

from . import history, ledger, local, read_github
from .git_source import verify_repository


def acquire(root, repository, base_ref, envelope, max_pages):
    verify_repository(root, repository)
    reference = local.checkout(root, base_ref)
    main_sha = (reference if base_ref == "origin/main" else local.checkout(root, "origin/main"))["base_sha"]
    return {
        "reference": reference,
        "collection_period": envelope.as_dict(),
        "github": read_github.collect(repository, envelope, max_pages),
        "ledger": ledger.capture(root),
        "main_history": history.capture(root, main_sha),
    }
