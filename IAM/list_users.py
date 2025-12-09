#!/usr/bin/env python3
"""List IAM user names with optional path prefix filtering."""

from __future__ import annotations

import argparse
import logging

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List IAM user names.")
    add_common_arguments(parser)
    parser.add_argument(
        "--path-prefix",
        default="/",
        help="Restrict listing to users under this path prefix (default '/').",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        iam_client = get_client(
            "iam", profile=args.profile, region=args.region or "us-east-1"
        )
        paginator = iam_client.get_paginator("list_users")
        for page in paginator.paginate(PathPrefix=args.path_prefix):
            for user in page.get("Users", []):
                print(user.get("UserName", ""))
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to list IAM users: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
