#!/usr/bin/env python3
"""List EBS snapshots for the current account with optional date filtering."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def _parse_tag_filters(tag_filters: List[str]) -> List[Dict[str, object]]:
    parsed: List[Dict[str, object]] = []
    for tag in tag_filters:
        if "=" not in tag:
            raise ValueError(f"Tag filter must be Key=Value (got {tag!r})")
        key, value = tag.split("=", 1)
        parsed.append({"Name": f"tag:{key}", "Values": [value]})
    return parsed


def iter_snapshots(
    *,
    profile: str | None,
    region: str | None,
    owner_ids: List[str],
    newer_than_days: int | None,
    tag_filters: List[str],
) -> Iterable[Dict[str, object]]:
    """Yield snapshots owned by the provided accounts."""
    client = get_client("ec2", profile=profile, region=region)
    filters: List[Dict[str, object]] = []
    if tag_filters:
        filters.extend(_parse_tag_filters(tag_filters))

    paginator = client.get_paginator("describe_snapshots")
    pagination_args: Dict[str, object] = {"OwnerIds": owner_ids}
    if filters:
        pagination_args["Filters"] = filters

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=newer_than_days)
        if newer_than_days is not None
        else None
    )

    for page in paginator.paginate(**pagination_args):
        for snap in page.get("Snapshots", []):
            start_time = snap.get("StartTime")
            if cutoff and start_time and start_time < cutoff:
                continue
            yield {
                "SnapshotId": snap.get("SnapshotId", ""),
                "VolumeId": snap.get("VolumeId", ""),
                "StartTime": start_time.isoformat() if start_time else "",
                "State": snap.get("State", ""),
                "OwnerId": snap.get("OwnerId", ""),
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List EBS snapshots for your account with optional filters."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--owner-id",
        action="append",
        default=[],
        help="Owner account ID (defaults to current caller).",
    )
    parser.add_argument(
        "--newer-than-days",
        type=int,
        help="Only include snapshots created within the last N days.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Filter snapshots by tag in Key=Value form.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    try:
        owner_ids = args.owner_id
        if not owner_ids:
            sts_client = get_client(
                "sts", profile=args.profile, region=args.region or "us-east-1"
            )
            owner_ids = [sts_client.get_caller_identity().get("Account", "")]

        for snap in iter_snapshots(
            profile=args.profile,
            region=args.region,
            owner_ids=owner_ids,
            newer_than_days=args.newer_than_days,
            tag_filters=args.tag,
        ):
            print(
                f"{snap['SnapshotId']}\t{snap['VolumeId']}\t"
                f"{snap['State']}\t{snap['StartTime']}\t{snap['OwnerId']}"
            )
    except ValueError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(2) from exc
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to list snapshots: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
