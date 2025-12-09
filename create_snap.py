#!/usr/bin/env python3
"""Preview which EBS volumes match the snapshot filters."""

from __future__ import annotations

import argparse
import logging
from typing import List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging
from resource_ebs_snap import find_volume_ids

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview volumes that match snapshot filters."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--state",
        action="append",
        default=["in-use"],
        help="Volume state filter (default: in-use).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=["Prod=backup", "Prod=Backup"],
        help="Tag filters in Key=Value form (defaults match Prod backup tags).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        volume_ids = find_volume_ids(
            profile=args.profile,
            region=args.region,
            states=args.state,
            tag_filters=args.tag,
        )
        if not volume_ids:
            LOGGER.warning("No volumes matched the provided filters.")
        for volume_id in volume_ids:
            print(volume_id)
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to describe volumes: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
