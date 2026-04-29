#!/usr/bin/env python3
from __future__ import annotations
import json
import requests

WEBHOOK_URL = "http://localhost:8000/webhook"

# Sửa nhanh biến này để test intent khác
TEST_MESSAGE = "cho mình xin link"
TEST_POST_ID = "1055755737627000_122000000000000001"
TEST_COMMENT_ID = "122999999999999001"
TEST_CUSTOMER_ID = "700000000000001"
TEST_CUSTOMER_NAME = "Test User"


def build_payload(message: str) -> dict:
    return {
        "object": "page",
        "entry": [
            {
                "id": "1055755737627000",
                "time": 1714381200000,
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "post_id": TEST_POST_ID,
                            "comment_id": TEST_COMMENT_ID,
                            "message": message,
                            "from": {
                                "id": TEST_CUSTOMER_ID,
                                "name": TEST_CUSTOMER_NAME,
                            },
                            "created_time": 1714381200,
                        },
                    }
                ],
            }
        ],
    }


def main():
    payload = build_payload(TEST_MESSAGE)
    print("=== SIMULATE WEBHOOK REQUEST ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
        print("\n=== WEBHOOK RESPONSE ===")
        print(f"status={resp.status_code}")
        try:
            print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
        except Exception:
            print(resp.text)
    except Exception as e:
        print("\n=== WEBHOOK ERROR ===")
        print(str(e))


if __name__ == "__main__":
    main()
