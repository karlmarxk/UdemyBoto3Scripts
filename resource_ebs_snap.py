#!/usr/bin/env python3
"""Create EBS snapshots for tagged volumes with sensible defaults."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client, get_resource

LOGGER = logging.getLogger(__name__)


def _parse_tag_filters(tag_filters: List[str]) -> List[Dict[str, object]]:
    parsed: List[Dict[str, object]] = []
    for tag in tag_filters:
        if "=" not in tag:
            raise ValueError(f"Tag filter must be Key=Value (got {tag!r})")
        key, value = tag.split("=", 1)
        parsed.append({"Name": f"tag:{key}", "Values": [value]})
    return parsed


def find_volume_ids(
    *,
    profile: str | None,
    region: str | None,
    states: List[str],
    tag_filters: List[str],
) -> List[str]:
    """Locate volume IDs that should be snapshotted."""
    ec2 = get_resource("ec2", profile=profile, region=region)
    filters: List[Dict[str, object]] = []
    if states:
        filters.append({"Name": "status", "Values": states})
    if tag_filters:
        filters.extend(_parse_tag_filters(tag_filters))

    volume_iter = ec2.volumes.filter(Filters=filters) if filters else ec2.volumes.all()
    volume_ids: List[str] = []
    for vol in volume_iter:
        LOGGER.debug("Found volume %s (%s)", vol.id, vol.state)
        volume_ids.append(vol.id)
    return volume_ids


def create_snapshots(
    *,
    profile: str | None,
    region: str | None,
    volume_ids: List[str],
    description: str,
    delete_on_days: int,
    dry_run: bool,
    wait: bool,
) -> List[str]:
    """Create snapshots for the provided volume IDs with tagging."""
    client = get_client("ec2", profile=profile, region=region)
    tag_specifications = [
        {
            "ResourceType": "snapshot",
            "Tags": [
                {"Key": "Delete-on", "Value": str(delete_on_days)},
            ],
        }
    ]
    snapshot_ids: List[str] = []
    for volume_id in volume_ids:
        try:
            response = client.create_snapshot(
                Description=description,
                VolumeId=volume_id,
                TagSpecifications=tag_specifications,
                DryRun=dry_run,
            )
            snapshot_id = response.get("SnapshotId")
            if snapshot_id:
                snapshot_ids.append(snapshot_id)
                LOGGER.info(
                    "Started snapshot %s for volume %s", snapshot_id, volume_id
                )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if dry_run and error_code == "DryRunOperation":
                LOGGER.info(
                    "Dry run succeeded for snapshot request on %s", volume_id
                )
                continue
            raise

    if wait and snapshot_ids and not dry_run:
        waiter = client.get_waiter("snapshot_completed")
        waiter.wait(SnapshotIds=snapshot_ids)

    return snapshot_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create EBS snapshots for volumes matching filters."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--state",
        action="append",
        default=["in-use"],
        help="Volume state filter (default: in-use). Can be given multiple times.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Volume tag filter in Key=Value form (can repeat).",
    )
    parser.add_argument(
        "--description",
        default="Automated snapshot via UdemyBoto3Scripts",
        help="Snapshot description to apply.",
    )
    parser.add_argument(
        "--delete-on",
        type=int,
        default=90,
        help="Value for Delete-on tag (days).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use EC2 DryRun to validate permissions without creating snapshots.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for snapshots to complete when not using dry-run.",
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
            return
        snapshot_ids = create_snapshots(
            profile=args.profile,
            region=args.region,
            volume_ids=volume_ids,
            description=args.description,
            delete_on_days=args.delete_on,
            dry_run=args.dry_run,
            wait=args.wait,
        )
        for snapshot_id in snapshot_ids:
            print(snapshot_id)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(2) from exc
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Snapshot creation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()


