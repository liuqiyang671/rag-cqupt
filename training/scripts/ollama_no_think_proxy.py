"""OpenAI-compatible proxy for Ollama chat with optional thinking control.

lm-evaluation-harness can call OpenAI-style chat completion endpoints, but
some Qwen thinking models served by Ollama return reasoning separately and
leave ``message.content`` empty on the OpenAI-compatible endpoint. This proxy
keeps the OpenAI-style route for lm_eval while forwarding requests to Ollama's
native ``/api/chat`` with an explicit ``think`` value.
"""
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import requests


DEFAULT_OLLAMA_URL = "http://localhost:11434"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_stop(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if item is not None and str(item)]


def _ollama_options(payload: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if "temperature" in payload and payload["temperature"] is not None:
        options["temperature"] = payload["temperature"]
    if "top_p" in payload and payload["top_p"] is not None:
        options["top_p"] = payload["top_p"]
    if "seed" in payload and payload["seed"] is not None:
        options["seed"] = payload["seed"]
    if "max_tokens" in payload and payload["max_tokens"] is not None:
        options["num_predict"] = int(payload["max_tokens"])

    stop = _clean_stop(payload.get("stop"))
    if stop:
        options["stop"] = stop
    return options


class OllamaNoThinkProxy(BaseHTTPRequestHandler):
    server_version = "OllamaNoThinkProxy/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in {"/health", "/v1/models"}:
            if self.path.rstrip("/") == "/health":
                self._write_json({"status": "ok"})
            else:
                self._write_json({"object": "list", "data": []})
            return
        self._write_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._write_json({"error": "only /v1/chat/completions is supported"}, status=404)
            return

        try:
            payload = self._read_json()
            response = self._chat_completion(payload)
        except Exception as exc:  # pragma: no cover - best effort server diagnostics
            self._write_json({"error": str(exc)}, status=500)
            return
        self._write_json(response)

    def _chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model") or self.server.default_model
        messages = payload.get("messages") or []
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        if payload.get("stream"):
            raise ValueError("stream=true is not supported by this proxy")

        ollama_payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": self.server.think,
            "options": _ollama_options(payload),
        }
        native_url = f"{self.server.ollama_url.rstrip('/')}/api/chat"
        native = requests.post(native_url, json=ollama_payload, timeout=self.server.timeout)
        native.raise_for_status()
        data = native.json()

        message = data.get("message") or {}
        content = message.get("content") or ""
        if not content and self.server.reasoning_fallback:
            content = message.get("reasoning") or message.get("thinking") or ""
        done_reason = data.get("done_reason") or "stop"
        finish_reason = "length" if done_reason == "length" else "stop"
        created = int(time.time())

        return {
            "id": f"chatcmpl-ollama-{created}",
            "object": "chat.completion",
            "created": created,
            "model": data.get("model") or model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
        }

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {self.client_address[0]} {fmt % args}")


class ProxyServer(ThreadingHTTPServer):
    ollama_url: str
    default_model: str
    timeout: int
    think: bool
    reasoning_fallback: bool


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI-compatible Ollama proxy with think=false")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11500)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--think", action="store_true", help="Enable Ollama thinking mode")
    parser.add_argument(
        "--reasoning-fallback",
        action="store_true",
        help="If content is empty, return reasoning/thinking text as OpenAI message.content",
    )
    args = parser.parse_args()

    server = ProxyServer((args.host, args.port), OllamaNoThinkProxy)
    server.ollama_url = args.ollama_url
    server.default_model = args.model
    server.timeout = args.timeout
    server.think = args.think
    server.reasoning_fallback = args.reasoning_fallback
    print(
        f"Proxy listening on http://{args.host}:{args.port}/v1/chat/completions "
        f"-> {args.ollama_url}/api/chat think={str(args.think).lower()}"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
