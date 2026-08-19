"""Import CMMS-to-DC asset mappings through the running API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://localhost:8000/sf_asset_mapping"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import an asset-mapping JSON file into digital_twin_simple."
    )
    parser.add_argument("json_file", type=Path)
    parser.add_argument(
        "--url",
        default=os.getenv("ASSET_MAPPING_API_URL", DEFAULT_URL),
        help=f"Mapping endpoint URL (default: {DEFAULT_URL})",
    )
    return parser.parse_args()


def load_payload(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if isinstance(payload, list):
        return {"mappings": payload}
    if isinstance(payload, dict) and isinstance(payload.get("mappings"), list):
        return payload
    raise ValueError(
        "The JSON must be a mapping list or an object containing a mappings list"
    )


def main() -> int:
    args = parse_args()
    api_key = os.getenv("MAPPING_ADMIN_API_KEY")
    if not api_key:
        print("MAPPING_ADMIN_API_KEY is required", file=sys.stderr)
        return 2

    try:
        payload = load_payload(args.json_file)
        request = Request(
            args.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Could not read the mapping file: {exc}", file=sys.stderr)
        return 2
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Mapping API returned HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Could not reach the mapping API: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("conflicts", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
