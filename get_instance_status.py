#!/usr/bin/env python3
"""Show EC2 status checks and lifecycle state for instances."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def iter_instance_statuses(
    *,
    profile: str | None,
    region: str | None,
    instance_ids: List[str],
    include_all: bool,
) -> Iterable[Dict[str, str]]:
    """Yield instance status check results."""
    client = get_client("ec2", profile=profile, region=region)
    paginator = client.get_paginator("describe_instance_status")
    pagination_args: Dict[str, object] = {
        "IncludeAllInstances": include_all,
    }
    if instance_ids:
        pagination_args["InstanceIds"] = instance_ids

    for page in paginator.paginate(**pagination_args):
        for status in page.get("InstanceStatuses", []):
            yield {
                "InstanceId": status.get("InstanceId", ""),
                "State": status.get("InstanceState", {}).get("Name", "unknown"),
                "SystemStatus": status.get("SystemStatus", {}).get(
                    "Status", "unknown"
                ),
                "InstanceStatus": status.get("InstanceStatus", {}).get(
                    "Status", "unknown"
                ),
                "AvailabilityZone": status.get("AvailabilityZone", ""),
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show EC2 status checks (system/instance) and lifecycle state."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--instance-id",
        action="append",
        default=[],
        help="Instance ID to inspect (can be set multiple times). Omit to scan all.",
    )
    parser.add_argument(
        "--include-stopped",
        action="store_true",
        help="Include stopped/terminated instances (uses IncludeAllInstances).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        for status in iter_instance_statuses(
            profile=args.profile,
            region=args.region,
            instance_ids=args.instance_id,
            include_all=args.include_stopped,
        ):
            print(
                f"{status['InstanceId']}\t{status['State']}\t"
                f"system={status['SystemStatus']}\tinstance={status['InstanceStatus']}\t"
                f"az={status['AvailabilityZone']}"
            )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Unable to fetch instance statuses: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
