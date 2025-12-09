#!/usr/bin/env python3
"""Show details for a specific IAM user."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_resource

LOGGER = logging.getLogger(__name__)


def describe_user(
    *, profile: str | None, region: str | None, user_name: str, include_groups: bool
) -> Dict[str, object]:
    iam = get_resource("iam", profile=profile, region=region or "us-east-1")
    user = iam.User(user_name)
    user.load()
    groups: List[str] = []
    if include_groups:
        groups = [group.name for group in user.groups.all()]
    return {
        "UserName": user.user_name,
        "UserId": user.user_id,
        "Arn": user.arn,
        "CreateDate": user.create_date.isoformat() if user.create_date else "",
        "Groups": groups,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Describe a single IAM user.")
    add_common_arguments(parser)
    parser.add_argument("user_name", help="IAM user name.")
    parser.add_argument(
        "--include-groups",
        action="store_true",
        help="List group memberships for the user.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        user = describe_user(
            profile=args.profile,
            region=args.region,
            user_name=args.user_name,
            include_groups=args.include_groups,
        )
        print(
            f"{user['UserName']}\t{user['UserId']}\t{user['Arn']}\t{user['CreateDate']}"
        )
        if args.include_groups and user["Groups"]:
            print("Groups:", ", ".join(user["Groups"]))
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to describe IAM user: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
