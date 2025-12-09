#!/usr/bin/env python3
"""Audit IAM access keys and optionally deactivate or delete stale keys."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def _iter_users(iam_client) -> Iterable[str]:
    paginator = iam_client.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page.get("Users", []):
            user_name = user.get("UserName")
            if user_name:
                yield user_name


def find_old_access_keys(
    *,
    iam_client,
    max_age_days: int,
    include_disabled: bool,
) -> Iterable[Dict[str, object]]:
    """Yield keys older than max_age_days with optional disabled-key inclusion."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    for user_name in _iter_users(iam_client):
        paginator = iam_client.get_paginator("list_access_keys")
        for page in paginator.paginate(UserName=user_name):
            for key in page.get("AccessKeyMetadata", []):
                status = key.get("Status")
                if status != "Active" and not include_disabled:
                    continue
                create_date: datetime = key.get("CreateDate")  # type: ignore[assignment]
                if create_date and create_date < cutoff:
                    last_used = iam_client.get_access_key_last_used(
                        AccessKeyId=key["AccessKeyId"]
                    ).get("AccessKeyLastUsed", {})
                    yield {
                        "UserName": user_name,
                        "AccessKeyId": key["AccessKeyId"],
                        "Status": status,
                        "CreateDate": create_date,
                        "LastUsed": last_used.get("LastUsedDate"),
                        "Region": last_used.get("Region"),
                    }


def deactivate_keys(iam_client, keys: List[Dict[str, object]]) -> None:
    for key in keys:
        iam_client.update_access_key(
            UserName=key["UserName"], AccessKeyId=key["AccessKeyId"], Status="Inactive"
        )
        LOGGER.info("Deactivated %s for %s", key["AccessKeyId"], key["UserName"])


def delete_keys(iam_client, keys: List[Dict[str, object]]) -> None:
    for key in keys:
        iam_client.delete_access_key(
            UserName=key["UserName"], AccessKeyId=key["AccessKeyId"]
        )
        LOGGER.info("Deleted %s for %s", key["AccessKeyId"], key["UserName"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report IAM access keys older than the configured age and optionally "
            "deactivate or delete them."
        )
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Report keys older than this many days (default: 90).",
    )
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include already disabled keys in the report.",
    )
    parser.add_argument(
        "--action",
        choices=["report", "deactivate", "delete"],
        default="report",
        help="What to do with old keys (default: report).",
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
        old_keys = list(
            find_old_access_keys(
                iam_client=iam_client,
                max_age_days=args.max_age_days,
                include_disabled=args.include_disabled,
            )
        )
        if not old_keys:
            print("No keys exceeded the age threshold.")
            return

        for key in old_keys:
            created = key["CreateDate"].isoformat() if key.get("CreateDate") else ""
            last_used = (
                key["LastUsed"].isoformat() if key.get("LastUsed") else "never"
            )
            print(
                f"{key['UserName']}\t{key['AccessKeyId']}\t{key['Status']}\t"
                f"created={created}\tlast_used={last_used}"
            )

        if args.action == "deactivate":
            deactivate_keys(iam_client, old_keys)
        elif args.action == "delete":
            delete_keys(iam_client, old_keys)
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Access key audit failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
