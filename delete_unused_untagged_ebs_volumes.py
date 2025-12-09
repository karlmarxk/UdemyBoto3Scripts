#!/usr/bin/env python3
"""Find and optionally delete unused, untagged EBS volumes."""

from __future__ import annotations

import argparse
import logging
from typing import List, Tuple

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client, get_resource

LOGGER = logging.getLogger(__name__)


def find_unused_untagged_volumes(
    *, profile: str | None, region: str | None
) -> List[Tuple[str, str]]:
    """Return (volume_id, state) for untagged, available volumes."""
    ec2 = get_resource("ec2", profile=profile, region=region)
    volumes = []
    for vol in ec2.volumes.filter(Filters=[{"Name": "status", "Values": ["available"]}]):
        if vol.tags:
            continue
        volumes.append((vol.id, vol.state))
    return volumes


def delete_volumes(
    *, profile: str | None, region: str | None, volume_ids: List[str], wait: bool
) -> None:
    """Delete the provided volumes and optionally wait for completion."""
    client = get_client("ec2", profile=profile, region=region)
    for volume_id in volume_ids:
        LOGGER.info("Deleting volume %s", volume_id)
        client.delete_volume(VolumeId=volume_id)

    if wait and volume_ids:
        waiter = client.get_waiter("volume_deleted")
        waiter.wait(VolumeIds=volume_ids)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Identify and delete unused, untagged EBS volumes."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the volumes (defaults to read-only).",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for deletion to finish when --apply is used.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        volumes = find_unused_untagged_volumes(
            profile=args.profile,
            region=args.region,
        )
        if not volumes:
            print("No unused, untagged volumes found.")
            return

        for volume_id, state in volumes:
            print(f"{volume_id}\t{state}")

        if args.apply:
            delete_volumes(
                profile=args.profile,
                region=args.region,
                volume_ids=[v[0] for v in volumes],
                wait=args.wait,
            )
            print("Deletion requested.")
        else:
            print("Dry run only. Re-run with --apply to delete volumes.")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Volume operation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()


