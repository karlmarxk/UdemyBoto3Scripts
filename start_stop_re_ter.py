#!/usr/bin/env python3
"""Start, stop, reboot, or terminate EC2 instances."""

from __future__ import annotations

import argparse
import logging
from typing import Callable, Dict, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


ACTION_WAITERS: Dict[str, str] = {
    "start": "instance_running",
    "stop": "instance_stopped",
    "terminate": "instance_terminated",
}


def change_state(
    *,
    profile: str | None,
    region: str | None,
    instance_ids: List[str],
    action: str,
    dry_run: bool,
    wait: bool,
) -> None:
    """Perform the requested state change with optional waiters."""
    client = get_client("ec2", profile=profile, region=region)
    operations: Dict[str, Callable[..., dict]] = {
        "start": client.start_instances,
        "stop": client.stop_instances,
        "reboot": client.reboot_instances,
        "terminate": client.terminate_instances,
    }
    operation = operations[action]
    try:
        response = operation(InstanceIds=instance_ids, DryRun=dry_run)
        LOGGER.debug("API response: %s", response)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if dry_run and error_code == "DryRunOperation":
            LOGGER.info("Dry run succeeded for %s on %s", action, instance_ids)
            return
        raise
    LOGGER.info("Requested %s on %s", action, instance_ids)

    if wait and action in ACTION_WAITERS:
        waiter = client.get_waiter(ACTION_WAITERS[action])
        LOGGER.info("Waiting for instances to reach state for %s", action)
        waiter.wait(InstanceIds=instance_ids)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely change EC2 instance state with optional waiters."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "action",
        choices=["start", "stop", "reboot", "terminate"],
        help="Action to perform.",
    )
    parser.add_argument(
        "instance_ids",
        nargs="+",
        help="One or more EC2 instance IDs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the EC2 DryRun safety check.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the target state before exiting.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        change_state(
            profile=args.profile,
            region=args.region,
            instance_ids=args.instance_ids,
            action=args.action,
            dry_run=args.dry_run,
            wait=args.wait,
        )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to change instance state: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
