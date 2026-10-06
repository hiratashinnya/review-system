"""公式 TypeSafe SDK の通信境界。HTTP timeout と全体期限を別に制限する。"""

import asyncio
import logging
from .configuration_failure import api_key
from .outbound_evidence import outbound_evidence, outbound_questions
from .redaction import known_secrets


async def request_answers(config: dict, evidence: dict, questions: dict):
    authorization_key = api_key(config)
    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

    # SDK debug は本文も記録するため、この専用プロセスでは通信ログを無効にする。
    for name in ("typesafe_sdk", "httpx2", "httpx", "httpcore"):
        logging.getLogger(name).disabled = True
    budget = float(config.get("timeout_seconds", 5))
    retry = RetryPolicy(max_retries=int(config.get("retries", 1)), timeout=budget)
    async with AsyncTypeSafeClient(
        api_key=authorization_key, model=config.get("model", "jev-1.13.0"),
        timeout=budget, retry=retry,
        base_url="https://api.typesafe.ai",
    ) as client:
        secrets = known_secrets(config, authorization_key)
        return await client.system_one(state=outbound_evidence(evidence, secrets),
                                       questions=outbound_questions(questions, secrets))


async def bounded_request(config: dict, evidence: dict, questions: dict):
    return await asyncio.wait_for(
        request_answers(config, evidence, questions),
        timeout=float(config.get("timeout_seconds", 5)),
    )
