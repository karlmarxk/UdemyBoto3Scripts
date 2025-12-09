#!/usr/bin/env python3
"""List AWS regions that support EC2."""

from __future__ import annotations

import argparse
import logging
from typing import List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def list_regions(
    *, profile: str | None, region: str | None, include_opt_in: bool
) -> List[str]:
    """Return EC2 region names, optionally including opt-in regions."""
    client = get_client("ec2", profile=profile, region=region)
    response = client.describe_regions(AllRegions=True)
    regions: List[str] = []
    for info in response.get("Regions", []):
        opt_in_status = info.get("OptInStatus")
        if not include_opt_in and opt_in_status not in (
            None,
            "opt-in-not-required",
        ):
            continue
        region_name = info.get("RegionName")
        if region_name:
            regions.append(region_name)
    return regions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List AWS regions that support EC2."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--include-opt-in",
        action="store_true",
        help="Include opt-in regions that are not currently enabled.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        regions = list_regions(
            profile=args.profile,
            region=args.region,
            include_opt_in=args.include_opt_in,
        )
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to retrieve regions: %s", exc)
        raise SystemExit(1) from exc

    for name in sorted(regions):
        print(name)


if __name__ == "__main__":
    main()
