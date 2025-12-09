#!/usr/bin/env python3
"""Create an IAM user with optional console password and managed policies."""

from __future__ import annotations

import argparse
import logging
import secrets
import string
from typing import List, Tuple

from botocore.exceptions import BotoCoreError, ClientError

from aws_utils import add_common_arguments, configure_logging, get_client

LOGGER = logging.getLogger(__name__)


def _secure_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_user(
    iam_client, *, user_name: str, tags: List[dict] | None = None
) -> Tuple[bool, dict]:
    """Create the user if needed; returns (created, user_dict)."""
    try:
        user = iam_client.get_user(UserName=user_name)
        return False, user["User"]
    except iam_client.exceptions.NoSuchEntity:
        response = iam_client.create_user(UserName=user_name, Tags=tags or [])
        return True, response["User"]


def attach_policies(iam_client, *, user_name: str, policies: List[str]) -> None:
    for policy in policies:
        iam_client.attach_user_policy(UserName=user_name, PolicyArn=policy)


def maybe_create_login_profile(
    iam_client, *, user_name: str, password: str | None, require_reset: bool
) -> str | None:
    if password is None:
        return None
    iam_client.create_login_profile(
        UserName=user_name,
        Password=password,
        PasswordResetRequired=require_reset,
    )
    return password


def maybe_create_access_key(iam_client, *, user_name: str) -> Tuple[str, str] | None:
    response = iam_client.create_access_key(UserName=user_name)
    key = response.get("AccessKey", {})
    access_key_id = key.get("AccessKeyId")
    secret = key.get("SecretAccessKey")
    if access_key_id and secret:
        return access_key_id, secret
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an IAM user with least-privilege defaults."
    )
    add_common_arguments(parser)
    parser.add_argument("user_name", help="IAM user name (not an email address).")
    parser.add_argument(
        "--policy-arn",
        action="append",
        default=["arn:aws:iam::aws:policy/ReadOnlyAccess"],
        help="Managed policy ARN to attach (can repeat). Defaults to ReadOnlyAccess.",
    )
    parser.add_argument(
        "--create-login",
        action="store_true",
        help="Create a console login profile with a generated password.",
    )
    parser.add_argument(
        "--password-reset-required",
        action="store_true",
        help="Require the user to reset the generated password on first login.",
    )
    parser.add_argument(
        "--create-access-key",
        action="store_true",
        help="Also create an access key (printed once; handle securely).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    try:
        iam_client = get_client(
            "iam", profile=args.profile, region=args.region or "us-east-1"
        )
        created, user = ensure_user(iam_client, user_name=args.user_name)
        if created:
            LOGGER.info("Created IAM user %s", args.user_name)
        else:
            LOGGER.info(
                "User %s already exists; will attach policies/keys as requested",
                args.user_name,
            )

        attach_policies(iam_client, user_name=args.user_name, policies=args.policy_arn)

        generated_password = None
        if args.create_login:
            generated_password = _secure_password()
            maybe_create_login_profile(
                iam_client,
                user_name=args.user_name,
                password=generated_password,
                require_reset=args.password_reset_required,
            )

        created_key = None
        if args.create_access_key:
            created_key = maybe_create_access_key(iam_client, user_name=args.user_name)

        print(f"IAM user: {user['UserName']} (Arn: {user['Arn']})")
        if generated_password:
            print("Console password (store securely):", generated_password)
        if created_key:
            access_key_id, secret = created_key
            print("AccessKeyId:", access_key_id)
            print("SecretAccessKey (store securely):", secret)
        if not generated_password and not created_key:
            print("No credentials were created (policies attached if provided).")
    except (BotoCoreError, ClientError) as exc:
        LOGGER.error("IAM user creation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
