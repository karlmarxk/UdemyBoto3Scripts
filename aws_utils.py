"""Shared helpers for boto3-based utility scripts.

This module centralizes safe boto3 session creation, retry-configured
client/resource builders, and consistent logging configuration so the
scripts can focus on the AWS task at hand while following current
security and resiliency practices (targeting boto3 releases current
through December 2025).
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config

# Align retries and user agent with modern AWS guidance.
_DEFAULT_CONFIG = Config(
    retries={"max_attempts": 10, "mode": "adaptive"},
    user_agent_extra="UdemyBoto3Scripts/2025-12",
)


def configure_logging(verbosity: int = 0) -> None:
    """Configure root logging once based on verbosity flag."""
    level = logging.WARNING
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    else:
        logging.getLogger().setLevel(level)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared CLI options for AWS profile/region and verbosity."""
    parser.add_argument(
        "--profile",
        help=(
            "Named AWS profile to use. Omit to rely on the default credential "
            "provider chain (env vars, SSO, instance roles, etc.)."
        ),
    )
    parser.add_argument(
        "--region",
        help=(
            "AWS region to target. Defaults to AWS_REGION/AWS_DEFAULT_REGION "
            "or the profile's configured region."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (can be specified multiple times).",
    )


def _resolve_region(session: boto3.session.Session, region: Optional[str]) -> str:
    """Return a concrete region, preferring CLI/env values over profile defaults."""
    resolved_region = (
        region
        or session.region_name
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
    )
    if not resolved_region:
        raise ValueError(
            "No AWS region configured. Set AWS_REGION/AWS_DEFAULT_REGION, "
            "configure a default region for the profile, or pass --region."
        )
    return resolved_region


def get_client(
    service_name: str,
    *,
    profile: Optional[str] = None,
    region: Optional[str] = None,
    config: Optional[Config] = None,
) -> boto3.session.Session.client:
    """Create a boto3 client with shared retry config and resolved region."""
    session_kwargs = {"profile_name": profile} if profile else {}
    session = boto3.session.Session(**session_kwargs)
    resolved_region = _resolve_region(session, region)
    return session.client(
        service_name, region_name=resolved_region, config=config or _DEFAULT_CONFIG
    )


def get_resource(
    service_name: str,
    *,
    profile: Optional[str] = None,
    region: Optional[str] = None,
    config: Optional[Config] = None,
) -> boto3.session.Session.resource:
    """Create a boto3 resource with shared retry config and resolved region."""
    session_kwargs = {"profile_name": profile} if profile else {}
    session = boto3.session.Session(**session_kwargs)
    resolved_region = _resolve_region(session, region)
    return session.resource(
        service_name, region_name=resolved_region, config=config or _DEFAULT_CONFIG
    )
