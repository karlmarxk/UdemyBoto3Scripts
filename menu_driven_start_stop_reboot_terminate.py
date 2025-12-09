#!/usr/bin/env python3
"""Interactive menu to start/stop/reboot/terminate EC2 instances."""

from __future__ import annotations

import argparse
import logging

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging
from start_stop_re_ter import change_state

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Menu-driven EC2 instance state helper (wraps start_stop_re_ter)."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use EC2 DryRun for safety checks.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the requested state change to complete.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    actions = {
        "1": "start",
        "2": "stop",
        "3": "reboot",
        "4": "terminate",
        "5": "exit",
    }

    while True:
        print("1. start\n2. stop\n3. reboot\n4. terminate\n5. Exit")
        option = input("Select an action (1-5): ").strip()
        action = actions.get(option)
        if action == "exit":
            print("Goodbye.")
            break
        if action is None:
            print("Invalid option. Please choose between 1-5.")
            continue
        instance_id = input("Enter the instance id: ").strip()
        try:
            change_state(
                profile=args.profile,
                region=args.region,
                instance_ids=[instance_id],
                action=action,
                dry_run=args.dry_run,
                wait=args.wait,
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.error("Unable to %s %s: %s", action, instance_id, exc)
            print(f"Failed to {action} {instance_id}: {exc}")


if __name__ == "__main__":
    main()

