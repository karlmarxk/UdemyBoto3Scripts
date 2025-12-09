#!/usr/bin/env python3
"""Create a bounded batch of IAM users (safe defaults, no infinite loops)."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def _parse_tags(tag_args: List[str]) -> List[Dict[str, str]]:
    tags: List[Dict[str, str]] = []
    for tag in tag_args:
        if "=" not in tag:
            raise ValueError(f"Tags must be Key=Value (got {tag!r})")
        key, value = tag.split("=", 1)
        tags.append({"Key": key, "Value": value})
    return tags


def create_users(
    *,
    profile: str | None,
    region: str | None,
    prefix: str,
    start: int,
    count: int,
    path: str,
    tags: List[Dict[str, str]],
    apply: bool,
) -> None:
    iam_client = get_client(
        "iam", profile=profile, region=region or "us-east-1"
    )
    for idx in range(start, start + count):
        user_name = f"{prefix}{idx}"
        if not apply:
            print(f"[dry-run] would create {user_name}")
            continue
        try:
            iam_client.create_user(UserName=user_name, Path=path, Tags=tags)
            print(f"Created user {user_name}")
        except iam_client.exceptions.EntityAlreadyExists:
            LOGGER.warning("User %s already exists; skipping", user_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create IAM users in bulk with bounds and optional tags."
    )
    add_common_arguments(parser)
    parser.add_argument("--prefix", default="demo-user-", help="Username prefix.")
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting suffix number (default: 1).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of users to create (default: 1).",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="IAM path prefix for the new users.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Tag to apply in Key=Value form (can repeat).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform creation. Default is dry-run.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        create_users(
            profile=args.profile,
            region=args.region,
            prefix=args.prefix,
            start=args.start,
            count=args.count,
            path=args.path,
            tags=_parse_tags(args.tag),
            apply=args.apply,
        )
    except ValueError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(2) from exc
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to create users: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
