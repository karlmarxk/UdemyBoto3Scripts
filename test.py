#!/usr/bin/env python3
"""Assume an IAM role and optionally print temporary credentials."""

from __future__ import annotations

import argparse
import logging
from typing import Dict

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def assume_role(
    *,
    profile: str | None,
    region: str | None,
    role_arn: str,
    session_name: str,
    duration: int,
) -> Dict[str, object]:
    sts_client = get_client(
        "sts", profile=profile, region=region or "us-east-1"
    )
    response = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=session_name, DurationSeconds=duration
    )
    return response.get("Credentials", {})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assume an IAM role using STS with minimal, secure output."
    )
    add_common_arguments(parser)
    parser.add_argument("role_arn", help="Role ARN to assume.")
    parser.add_argument(
        "--session-name",
        default="UdemyBoto3ScriptsSession",
        help="Friendly session name for the STS call.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=3600,
        help="Session duration in seconds (default: 3600).",
    )
    parser.add_argument(
        "--show-credentials",
        action="store_true",
        help="Print temporary access key/secret/token (handle securely).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        credentials = assume_role(
            profile=args.profile,
            region=args.region,
            role_arn=args.role_arn,
            session_name=args.session_name,
            duration=args.duration_seconds,
        )
        if not credentials:
            print("AssumeRole response did not return credentials.")
            return

        print("Successfully assumed role.")
        if args.show_credentials:
            print("AccessKeyId:", credentials.get("AccessKeyId"))
            print("SecretAccessKey:", credentials.get("SecretAccessKey"))
            print("SessionToken:", credentials.get("SessionToken"))
            print("Expiration:", credentials.get("Expiration"))
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("AssumeRole failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
