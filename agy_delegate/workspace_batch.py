"""同workspace順次バッチ、別workspace有限並列。"""

from concurrent.futures import ThreadPoolExecutor

from .types import Request, Result


def wait_budget(request: Request) -> int:
    return request.print_timeout + 10 if type(request.print_timeout) is int else 130

def run_parallel(requests: list[Request], *, max_concurrency: int,
                 ) -> list[Result]:
    """結果順は入力順。1件失敗を全体成功へ集約しない。"""
    if not 1 <= max_concurrency <= 8:
        raise ValueError("parallel_limit_invalid")
    groups = {}
    for index, request in enumerate(requests):
        groups.setdefault(request.workspace.resolve(), []).append((index, request))
    results = [None] * len(requests)
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = [pool.submit(_run_workspace_batch, group) for group in groups.values()]
        for future in futures:
            for index, result in future.result():
                results[index] = result
    return results

def _run_workspace_batch(group):
    from .runner import _run
    results, preceding_budget = [], 0
    for index, request in group:
        budget = wait_budget(request)
        results.append((index, _run(request, preceding_budget + budget)))
        preceding_budget += budget
    return results
