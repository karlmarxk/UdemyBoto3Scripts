#!/usr/bin/env python3
"""List unused, untagged EBS volumes (read-only helper)."""

from __future__ import annotations

import argparse
import logging

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging
from delete_unused_untagged_ebs_volumes import find_unused_untagged_volumes

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List unused and untagged EBS volumes without deleting them."
    )
    add_common_arguments(parser)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        volumes = find_unused_untagged_volumes(
            profile=args.profile, region=args.region
        )
        if not volumes:
            print("No unused, untagged volumes found.")
            return
        for volume_id, state in volumes:
            print(f"{volume_id}\t{state}")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to list volumes: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
