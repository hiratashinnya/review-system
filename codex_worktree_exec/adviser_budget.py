"""相談の整数予算とtrusted経過時間を同じ境界で検証する。"""
import math

INTEGER_BUDGETS = {"max_calls", "calls_used", "max_tokens", "tokens_used", "reserve_tokens",
                   "max_cost_microusd", "cost_used_microusd", "reserve_cost_microusd"}
TIME_BUDGETS = {"max_seconds", "seconds_used", "reserve_seconds"}


def seconds(value):
    if type(value) not in (int, float) or value < 0:
        raise ValueError("invalid elapsed seconds")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("invalid elapsed seconds")
    return value


def validate_budget(raw):
    for key in INTEGER_BUDGETS:
        if type(raw[key]) is not int or raw[key] < 0:
            raise ValueError(f"invalid budget {key}")
    for key in TIME_BUDGETS:
        seconds(raw[key])
    if (raw["calls_used"] >= raw["max_calls"] or raw["reserve_tokens"] <= 0
            or raw["reserve_seconds"] <= 0 or raw["reserve_cost_microusd"] <= 0):
        raise ValueError("adviser budget reached")
    for used, reserve, maximum in (("tokens_used", "reserve_tokens", "max_tokens"),
                                  ("seconds_used", "reserve_seconds", "max_seconds"),
                                  ("cost_used_microusd", "reserve_cost_microusd", "max_cost_microusd")):
        if raw[used] >= raw[maximum] or raw[used] + raw[reserve] > raw[maximum]:
            raise ValueError("adviser budget reached")
