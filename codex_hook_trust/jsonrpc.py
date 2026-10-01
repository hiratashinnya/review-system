"""Line-oriented JSON-RPC helpers for Codex app-server."""

from __future__ import annotations

import json
import queue
import threading
import time


def _read_lines(stream, messages):
    try:
        for line in stream:
            messages.put(line)
    except Exception as error:  # noqa: BLE001 - transport failure for caller
        messages.put(error)
    finally:
        messages.put(None)


def start_reader(stream):
    messages = queue.Queue()
    threading.Thread(target=_read_lines, args=(stream, messages), daemon=True).start()
    return messages


def send_message(stream, message):
    stream.write(json.dumps(message) + "\n")
    stream.flush()


def read_result(messages, request_id, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("app-server response timed out")
        try:
            line = messages.get(timeout=remaining)
        except queue.Empty as error:
            raise TimeoutError("app-server response timed out") from error
        if line is None:
            raise RuntimeError("app-server closed stdout before replying")
        if isinstance(line, Exception):
            raise RuntimeError("could not read app-server response") from line
        message = json.loads(line)
        if not isinstance(message, dict):
            raise ValueError("invalid JSON-RPC message")
        if "method" in message:
            if "id" not in message:
                continue
            # Without a request handler, continuing could miss the server's trust result.
            raise ValueError("unexpected app-server request")
        if message.get("id") != request_id:
            raise ValueError("unexpected JSON-RPC response id")
        if "error" in message:
            raise RuntimeError("app-server returned a JSON-RPC error")
        result = message.get("result")
        if not isinstance(result, dict):
            raise ValueError("JSON-RPC result must be an object")
        return result
