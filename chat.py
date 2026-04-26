#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import List, Dict

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CLI chat client for local Ollama API bridge")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Base URL of API bridge")
    parser.add_argument("--model", default="llama3.1:8b", help="Ollama model name")
    parser.add_argument("--system", default="You are a concise and helpful assistant.", help="System prompt")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max output tokens")
    parser.add_argument("--timeout", type=float, default=90.0, help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=1, help="Retry count for transient failures")
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional API key sent as X-API-Key (or set API_AUTH_TOKEN env var)",
    )
    parser.add_argument("--oneshot", help="Single prompt mode. Prints one reply and exits")
    return parser.parse_args()


def request_chat(
    api_base: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_seconds: float = 90.0,
    retries: int = 1,
    api_key: str = "",
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    safe_retries = max(0, retries)
    attempts = safe_retries + 1
    timeout = httpx.Timeout(timeout_seconds, connect=5.0)

    for attempt in range(1, attempts + 1):
        try:
            headers = {"X-API-Key": api_key} if api_key else None
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{api_base}/chat", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            if attempt < attempts:
                continue
            raise RuntimeError(f"Chat request failed: {exc}") from exc

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = resp.text

            if resp.status_code >= 500 and attempt < attempts:
                continue
            raise RuntimeError(f"Chat request failed ({resp.status_code}): {detail}")

        data = resp.json()
        return data["message"]["content"]

    raise RuntimeError("Chat request failed")


def print_help_hint() -> None:
    print("Type /exit to quit, /reset to clear history, /history to print conversation.")


def repl(args: argparse.Namespace) -> int:
    messages: List[Dict[str, str]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})

    print(f"Connected to {args.api} using model '{args.model}'.")
    print_help_hint()

    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0

        if not user_text:
            continue

        if user_text == "/exit":
            print("bye")
            return 0

        if user_text == "/reset":
            messages = [{"role": "system", "content": args.system}] if args.system else []
            print("history cleared")
            continue

        if user_text == "/history":
            print(json.dumps(messages, indent=2))
            continue

        messages.append({"role": "user", "content": user_text})

        try:
            answer = request_chat(
                api_base=args.api,
                model=args.model,
                messages=messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout,
                retries=args.retries,
                api_key=args.api_key or os.getenv("API_AUTH_TOKEN", ""),
            )
        except RuntimeError as exc:
            print(f"error: {exc}")
            continue

        print(f"assistant> {answer}")
        messages.append({"role": "assistant", "content": answer})


def oneshot(args: argparse.Namespace) -> int:
    messages: List[Dict[str, str]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.oneshot})

    try:
        answer = request_chat(
            api_base=args.api,
            model=args.model,
            messages=messages,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout,
            retries=args.retries,
            api_key=args.api_key or os.getenv("API_AUTH_TOKEN", ""),
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(answer)
    return 0


def main() -> int:
    args = parse_args()
    if args.oneshot:
        return oneshot(args)
    return repl(args)


if __name__ == "__main__":
    raise SystemExit(main())
