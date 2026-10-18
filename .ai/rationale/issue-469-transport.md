# Issue #469: GitHub transport contract

## Decision

Rename `ReadTransport` to `GitHubApiTransport` and `UrlLibReadTransport` to `UrlLibGitHubApiTransport`. The class documentation states that it sends GET and POST requests and that POST can change GitHub state. `GitHubCollector` remains a read-oriented collector; its transport dependency now describes only the HTTP capabilities it actually exposes.

The alternatives were a docstring-only correction, query-only mutation rejection, or renaming the read-specific contract. A docstring-only correction would leave `ReadTransport` inaccurate. Mutation rejection would require parsing every GraphQL request body and would change request behavior; the blocker gate currently uses POST only for GraphQL reads. Renaming is the smallest complete correction to the name and documented capability. Callers must not infer a read-only guarantee from this generic transport.

## `project_status_sync` relationship

Keep `project_status_sync/github.py`'s `Transport` and `UrlLibTransport` independent. It owns the Projects V2 authentication requirement, project-specific response validation, and an intentional `updateProjectV2ItemFieldValue` mutation. Sharing a lower-level urllib wrapper would not establish a read/write boundary and would couple separate API error and credential contracts. Both adapters may keep their small standard-library HTTP handling in their owning domain modules.
