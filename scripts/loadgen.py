"""Send predictions to the API in a loop

    python scripts/loadgen.py

We only use packages available in standard lib of Python
"""

import glob
import json
import os
import random
import time
import urllib.error
import urllib.request

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8000")
PAYLOAD_GLOB = os.environ.get("PAYLOAD_GLOB", "scripts/payload*.json")
DELAY_S = float(os.environ.get("DELAY_S", "1"))
API_TOKEN = os.environ["ML520_SECURITY__API_TOKEN"]


def send_one(payload: dict) -> str:
    """Send a request to the target endpoint and return a description of output"""
    request = urllib.request.Request(
        f"{TARGET_URL}/v1/predict",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "ML520-API-Key": API_TOKEN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.load(response)
            return f"{response.status} prediction={body['prediction']} served_by={response.headers.get('X-Served-By')}"
    except urllib.error.HTTPError as error:
        return f"{error.code} {error.reason}"
    except urllib.error.URLError as error:
        return f"unreachable {error.reason}"


def main() -> None:
    payloads = [json.loads(open(path).read()) for path in sorted(glob.glob(PAYLOAD_GLOB))]
    if not payloads:
        raise SystemExit(f"no payload matched {PAYLOAD_GLOB}")

    print(f"sending {len(payloads)} payloads to {TARGET_URL} every {DELAY_S}s", flush=True)
    while True:
        print(send_one(random.choice(payloads)), flush=True)
        time.sleep(DELAY_S)


if __name__ == "__main__":
    main()
