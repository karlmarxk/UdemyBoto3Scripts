#!/usr/bin/env python3
"""Print the AWS account ID for the active credentials."""

from __future__ import annotations

import argparse
import logging

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show the AWS account ID for the configured credentials."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--include-arn",
        action="store_true",
        help="Also print the ARN for the active identity.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    try:
        sts_client = get_client(
            "sts", profile=args.profile, region=args.region or "us-east-1"
        )
        identity = sts_client.get_caller_identity()
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("Unable to resolve account identity: %s", exc)
        raise SystemExit(1) from exc

    print(identity.get("Account", "unknown"))
    if args.include_arn:
        print(identity.get("Arn", "unknown"))


if __name__ == "__main__":
    main()
