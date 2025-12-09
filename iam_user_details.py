#!/usr/bin/env python3
"""Show group and policy attachments for an IAM user."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def get_user_membership(
    *, profile: str | None, region: str | None, user_name: str, include_policies: bool
) -> Dict[str, List[str]]:
    iam_client = get_client(
        "iam", profile=profile, region=region or "us-east-1"
    )
    groups = [
        group["GroupName"]
        for group in iam_client.list_groups_for_user(UserName=user_name).get(
            "Groups", []
        )
    ]
    policies: List[str] = []
    if include_policies:
        paginator = iam_client.get_paginator("list_attached_user_policies")
        for page in paginator.paginate(UserName=user_name):
            for policy in page.get("AttachedPolicies", []):
                policies.append(policy.get("PolicyArn", ""))
    return {"Groups": groups, "Policies": policies}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show group memberships and attached policies for an IAM user."
    )
    add_common_arguments(parser)
    parser.add_argument("user_name", help="IAM user name to inspect.")
    parser.add_argument(
        "--include-policies",
        action="store_true",
        help="Also list attached managed policies.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        membership = get_user_membership(
            profile=args.profile,
            region=args.region,
            user_name=args.user_name,
            include_policies=args.include_policies,
        )
        if membership["Groups"]:
            print("Groups:", ", ".join(membership["Groups"]))
        else:
            print("Groups: none")
        if args.include_policies:
            if membership["Policies"]:
                print("Policies:", ", ".join(membership["Policies"]))
            else:
                print("Policies: none")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to describe IAM user membership: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
