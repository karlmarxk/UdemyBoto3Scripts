#!/usr/bin/env python3
"""List S3 buckets or objects using the configured AWS credentials."""

from __future__ import annotations

import argparse
import logging
from typing import Iterable, List

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def list_buckets(*, profile: str | None, region: str | None) -> List[str]:
    """Return all bucket names visible to the caller."""
    s3_client = get_client("s3", profile=profile, region=region)
    response = s3_client.list_buckets()
    return [bucket["Name"] for bucket in response.get("Buckets", [])]


def list_objects(
    *,
    bucket: str,
    prefix: str,
    profile: str | None,
    region: str | None,
    max_keys: int = 1000,
) -> Iterable[str]:
    """Yield object keys for the specified bucket."""
    s3_client = get_client("s3", profile=profile, region=region)
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": max_keys}
    ):
        for obj in page.get("Contents", []):
            key = obj.get("Key")
            if key is not None:
                yield key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List S3 buckets or objects with modern boto3 practices."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--bucket",
        help="If provided, list objects in this bucket instead of listing buckets.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Prefix filter when listing objects (defaults to empty string).",
    )
    parser.add_argument(
        "--max-keys",
        type=int,
        default=1000,
        help="Page size for listing objects.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    try:
        if args.bucket:
            for key in list_objects(
                bucket=args.bucket,
                prefix=args.prefix,
                profile=args.profile,
                region=args.region,
                max_keys=args.max_keys,
            ):
                print(key)
        else:
            for name in list_buckets(profile=args.profile, region=args.region):
                print(name)
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("S3 operation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
