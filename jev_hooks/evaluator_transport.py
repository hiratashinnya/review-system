"""公式 TypeSafe SDK の通信境界。HTTP timeout と全体期限を別に制限する。"""

import asyncio
import logging
import os


async def request_answers(config: dict, evidence: dict, questions: dict):
    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

    # SDK debug は本文も記録するため、この専用プロセスでは通信ログを無効にする。
    for name in ("typesafe_sdk", "httpx2", "httpx", "httpcore"):
        logging.getLogger(name).disabled = True
    budget = float(config.get("timeout_seconds", 5))
    retry = RetryPolicy(max_retries=int(config.get("retries", 1)), timeout=budget)
    api_key = os.environ.get(config.get("api_key_env", "TYPESAFE_API_KEY"), "")
    if not api_key:
        raise ValueError("missing_api_key")
    async with AsyncTypeSafeClient(
        api_key=api_key, model=config.get("model", "jev-1.13.0"),
        timeout=budget, retry=retry,
        base_url="https://api.typesafe.ai",
    ) as client:
        return await client.system_one(state=evidence, questions=questions)


async def bounded_request(config: dict, evidence: dict, questions: dict):
    return await asyncio.wait_for(
        request_answers(config, evidence, questions),
        timeout=float(config.get("timeout_seconds", 5)),
    )
