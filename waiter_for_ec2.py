#!/usr/bin/env python3
"""Wait for an EC2 instance to reach a target lifecycle state."""

from __future__ import annotations

import argparse
import logging
from typing import List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def wait_for_state(
    *, profile: str | None, region: str | None, instance_ids: List[str], waiter: str
) -> None:
    """Block until the requested waiter condition is met."""
    client = get_client("ec2", profile=profile, region=region)
    waiter_obj = client.get_waiter(waiter)
    LOGGER.info("Waiting on %s for instances: %s", waiter, instance_ids)
    waiter_obj.wait(InstanceIds=instance_ids)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use EC2 waiters to block until instances reach a given state."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "instance_ids",
        nargs="+",
        help="Instance IDs to wait on.",
    )
    parser.add_argument(
        "--waiter",
        choices=["instance_running", "instance_stopped", "instance_terminated"],
        default="instance_running",
        help="Waiter to use (defaults to instance_running).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        wait_for_state(
            profile=args.profile,
            region=args.region,
            instance_ids=args.instance_ids,
            waiter=args.waiter,
        )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Waiter failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
