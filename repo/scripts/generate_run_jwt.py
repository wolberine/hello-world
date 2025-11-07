from __future__ import annotations

import argparse
import uuid

from app.core.security import create_run_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a short-lived run JWT")
    parser.add_argument("user_id", help="User UUID")
    parser.add_argument("run_id", help="Run UUID", nargs="?", default=str(uuid.uuid4()))
    parser.add_argument("mode", choices=["preview", "execute"], default="preview")
    args = parser.parse_args()

    token = create_run_token(args.user_id, ["report", "email"], extra={"run_id": args.run_id, "mode": args.mode})
    print(token)


if __name__ == "__main__":
    main()
