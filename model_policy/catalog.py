"""Codex debug models と、同一 Copilot surface の一覧を正規化する。"""

import json
import re
import subprocess
from datetime import datetime, timezone

from .codex_auth import codex_auth_mode

MAX_CATALOG_AGE_SECONDS = 900


def codex_catalog(runner=subprocess.run, auth_mode=None):
    auth_mode = codex_auth_mode(runner) if auth_mode is None else auth_mode
    if auth_mode not in ("backend", "api"):
        raise ValueError("STOP: Codex 認証方式が不明です")
    completed = runner(["codex", "debug", "models"], capture_output=True,
                       text=True, check=True, timeout=60)
    if any(re.search(r"error|failed|fallback", line, re.I)
           and re.search(r"model|catalog|refresh", line, re.I)
           for line in (completed.stderr or "").splitlines()):
        raise ValueError("STOP: Codex 一覧の refresh エラーを検出しました")
    payload = json.loads(completed.stdout)
    models = payload["models"]
    if not isinstance(models, list):
        raise ValueError("STOP: Codex 一覧は models 配列が必要です")
    result = []
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("slug"), str):
            raise ValueError("STOP: Codex 一覧の slug が不正です")
        if model.get("visibility") == "list" and (auth_mode == "backend" or model.get("supported_in_api") is True):
            result.append({"id": model["slug"]})
    return result


def copilot_catalog(path, surface):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["surface"] != surface or not payload.get("observed_at"):
        raise ValueError("STOP: Copilot 一覧の surface/観測日時が一致しません")
    observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
    if observed.utcoffset() != timezone.utc.utcoffset(observed):
        raise ValueError("STOP: 観測日時は UTC offset が必要です")
    age = (datetime.now(timezone.utc) - observed).total_seconds()
    if not 0 <= age <= MAX_CATALOG_AGE_SECONDS:
        raise ValueError("STOP: Copilot 一覧は準備前15分以内の取得が必要です")
    if payload.get("source") not in ("sdk.listModels", "vscode.lm.selectChatModels", "/model"):
        raise ValueError("STOP: Copilot 一覧の取得元が不正です")
    if payload["source"] == "/model" and (not isinstance(payload.get("manual_reason"), str)
                                          or not payload["manual_reason"].strip()):
        raise ValueError("STOP: 手動一覧には機械的取得が使えない理由が必要です")
    if surface == "ide" and payload["source"] != "vscode.lm.selectChatModels":
        raise ValueError("STOP: CLI 一覧は IDE に流用できません")
    if surface == "cli" and payload["source"] == "vscode.lm.selectChatModels":
        raise ValueError("STOP: IDE 一覧は CLI に流用できません")
    models = payload["models"]
    if not isinstance(models, list):
        raise ValueError("STOP: Copilot 一覧は models 配列が必要です")
    available = []
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("STOP: Copilot モデル項目が不正です")
        policy = model.get("policy", {})
        if not isinstance(policy, dict) or ("available" in model and type(model["available"]) is not bool):
            raise ValueError("STOP: Copilot モデルの利用可否が不正です")
        if "state" in policy and policy["state"] not in ("enabled", "disabled", "unconfigured"):
            raise ValueError("STOP: Copilot policy state が不正です")
        if model.get("available") is False or policy.get("state") == "disabled":
            continue
        available.append(model)
    return available, payload
