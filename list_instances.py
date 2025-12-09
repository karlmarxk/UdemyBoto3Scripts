#!/usr/bin/env python3
"""List EC2 instances with optional state and tag filtering."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def _parse_tag_filters(tag_filters: List[str]) -> List[Dict[str, str]]:
    parsed_filters: List[Dict[str, str]] = []
    for tag in tag_filters:
        if "=" not in tag:
            raise ValueError(f"Tag filter must be in Key=Value form (got {tag!r})")
        key, value = tag.split("=", 1)
        parsed_filters.append({"Name": f"tag:{key}", "Values": [value]})
    return parsed_filters


def iter_instances(
    *, profile: str | None, region: str | None, states: List[str], tag_filters: List[str]
) -> Iterable[Dict[str, str]]:
    """Yield instance details matching the provided filters."""
    client = get_client("ec2", profile=profile, region=region)
    filters: List[Dict[str, object]] = []
    if states:
        filters.append({"Name": "instance-state-name", "Values": states})
    if tag_filters:
        filters.extend(_parse_tag_filters(tag_filters))

    paginator = client.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=filters):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                yield {
                    "InstanceId": instance.get("InstanceId", ""),
                    "InstanceType": instance.get("InstanceType", ""),
                    "State": instance.get("State", {}).get("Name", "unknown"),
                    "Name": next(
                        (
                            tag["Value"]
                            for tag in instance.get("Tags", [])
                            if tag.get("Key") == "Name"
                        ),
                        "",
                    ),
                }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List EC2 instances with modern boto3 usage."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--state",
        action="append",
        default=[],
        help="Filter by instance state (can be provided multiple times).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Filter by tag in Key=Value form (can be provided multiple times).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    try:
        for inst in iter_instances(
            profile=args.profile,
            region=args.region,
            states=args.state,
            tag_filters=args.tag,
        ):
            print(
                f"{inst['InstanceId']}\t{inst['State']}\t{inst['InstanceType']}\t"
                f"{inst['Name']}"
            )
    except ValueError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(2) from exc
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Failed to describe instances: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
