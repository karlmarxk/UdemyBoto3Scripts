#!/usr/bin/env python3
"""Quickly show the state of one or more EC2 instances."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_resource

LOGGER = logging.getLogger(__name__)


def describe_states(
    *, profile: str | None, region: str | None, instance_ids: List[str]
) -> Iterable[Dict[str, str]]:
    """Yield state names using the resource API to demonstrate both SDK styles."""
    ec2 = get_resource("ec2", profile=profile, region=region)
    for instance_id in instance_ids:
        instance = ec2.Instance(instance_id)
        instance.load()
        yield {
            "InstanceId": instance_id,
            "State": instance.state.get("Name", "unknown"),
            "Type": instance.instance_type,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get the current state for one or more EC2 instances."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "instance_ids",
        nargs="+",
        help="One or more EC2 instance IDs.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        for info in describe_states(
            profile=args.profile, region=args.region, instance_ids=args.instance_ids
        ):
            print(f"{info['InstanceId']}\t{info['State']}\t{info['Type']}")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to load instance state: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
