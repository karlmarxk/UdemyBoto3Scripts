#!/usr/bin/env python3
"""Describe EC2 instance states via the EC2 client."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def iter_instance_states(
    *, profile: str | None, region: str | None, instance_ids: List[str]
) -> Iterable[Dict[str, str]]:
    """Yield state details for provided instance IDs (or all instances if none)."""
    client = get_client("ec2", profile=profile, region=region)
    if instance_ids:
        reservations = client.describe_instances(InstanceIds=instance_ids).get(
            "Reservations", []
        )
        iterable = reservations
    else:
        paginator = client.get_paginator("describe_instances")
        iterable = (
            reservation
            for page in paginator.paginate()
            for reservation in page.get("Reservations", [])
        )

    for reservation in iterable:
        for instance in reservation.get("Instances", []):
            yield {
                "InstanceId": instance.get("InstanceId", ""),
                "State": instance.get("State", {}).get("Name", "unknown"),
                "InstanceType": instance.get("InstanceType", ""),
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show EC2 instance states using describe_instances."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--instance-id",
        action="append",
        default=[],
        help="Instance ID to describe (can be specified multiple times).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        for info in iter_instance_states(
            profile=args.profile, region=args.region, instance_ids=args.instance_id
        ):
            print(
                f"{info['InstanceId']}\t{info['State']}\t{info['InstanceType']}"
            )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to describe instance states: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
