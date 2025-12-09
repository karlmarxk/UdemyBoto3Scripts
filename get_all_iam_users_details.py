#!/usr/bin/env python3
"""List IAM users with creation date and ARN."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def iter_users(
    *, profile: str | None, region: str | None, include_path: bool
) -> Iterable[Dict[str, str]]:
    iam_client = get_client(
        "iam", profile=profile, region=region or "us-east-1"
    )
    paginator = iam_client.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page.get("Users", []):
            yield {
                "UserName": user.get("UserName", ""),
                "UserId": user.get("UserId", ""),
                "Arn": user.get("Arn", ""),
                "CreateDate": user.get("CreateDate"),
                "Path": user.get("Path", "") if include_path else "",
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List IAM users with basic metadata."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--include-path",
        action="store_true",
        help="Include the path prefix in the output.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        for user in iter_users(
            profile=args.profile, region=args.region, include_path=args.include_path
        ):
            created = user["CreateDate"].isoformat() if user["CreateDate"] else ""
            print(
                f"{user['UserName']}\t{user['UserId']}\t{user['Arn']}\t"
                f"{created}\t{user['Path']}"
            )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to list IAM users: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
