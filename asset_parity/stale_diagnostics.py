"""Interpret raw last-commit observations without changing the flag."""

from .stale_signal import StaleSignal


def time_direction(signal: StaleSignal) -> str:
    if signal.parity_seed_epoch is None or signal.mirror_epoch is None:
        return "unobservable"
    if signal.parity_seed_epoch > signal.mirror_epoch:
        return "parity seed newer"
    if signal.parity_seed_epoch < signal.mirror_epoch:
        return "mirror newer"
    return "same time"
