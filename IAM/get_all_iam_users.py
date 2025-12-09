#!/usr/bin/env python3
"""Export IAM users to stdout or CSV."""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def fetch_users(*, profile: str | None, region: str | None) -> List[dict]:
    iam_client = get_client(
        "iam", profile=profile, region=region or "us-east-1"
    )
    paginator = iam_client.get_paginator("list_users")
    users: List[dict] = []
    for page in paginator.paginate():
        users.extend(page.get("Users", []))
    return users


def write_csv(path: Path, users: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["UserName", "UserId", "Arn", "CreateDate", "Path"])
        for user in users:
            writer.writerow(
                [
                    user.get("UserName", ""),
                    user.get("UserId", ""),
                    user.get("Arn", ""),
                    user.get("CreateDate", ""),
                    user.get("Path", ""),
                ]
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List IAM users and optionally export to CSV."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--csv-out",
        type=Path,
        help="Write user data to this CSV file (in addition to stdout).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        users = fetch_users(profile=args.profile, region=args.region)
        for user in users:
            print(user.get("UserName", ""))

        if args.csv_out:
            write_csv(args.csv_out, users)
            print(f"Wrote {len(users)} users to {args.csv_out}")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to list IAM users: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

