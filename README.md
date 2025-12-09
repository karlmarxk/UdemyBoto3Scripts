# UdemyBoto3Scripts

Modernized boto3 utility scripts for common AWS tasks (EC2, EBS, IAM, S3, and STS) with security-focused defaults and PEP8-compliant Python 3 code.

## Prerequisites
- Python 3.10+ and `boto3>=1.34` (aligned with AWS APIs current through Dec 2025).
- AWS credentials/SSO configured via the standard credential chain. Set `AWS_REGION`/`AWS_DEFAULT_REGION` or pass `--region`.
- Install deps: `python3 -m pip install -U boto3 botocore`.

## Shared CLI options
Most scripts accept:
- `--profile` to pick an AWS named profile.
- `--region` to override the target region.
- `-v/--verbose` for INFO, `-vv` for DEBUG logging.

## Security & resiliency practices
- No embedded credentials or admin policies by default; IAM scripts default to read-only policies.
- Support for dry-run or explicit `--apply` flags before destructive changes.
- Centralized retry/user agent config in `aws_utils.py` with modern boto3 waiters/paginators.
- Outputs avoid secrets unless explicitly requested (e.g., `--create-access-key`, `--show-credentials`).

## Script highlights
- **EC2**: `list_instances.py`, `get_inst_state_using_client.py`, `get_instance_status.py`, `status_of_instance.py`, `start_stop_re_ter.py`, `menu_driven_start_stop_reboot_terminate.py`, `waiter_for_ec2.py`, `get_all_regions_for_ec2_service.py`.
- **EBS**: `resource_ebs_snap.py` (snapshot creation with tags/waiters), `create_snap.py` (preview targets), `automate_ebs_snaps.py` (wrapper), `delete_unused_untagged_ebs_volumes.py`/`unuser_untagged_volumes.py` (safe cleanup), `get_all_snapshots.py`/`list_snapshots.py` (snapshot listing).
- **IAM**: `get_all_iam_users_details.py`, `get_iam_user_details.py`, `iam_user_details.py` (groups/policies), `access_keys.py` (aged-key audit), `create_an_iam_user_console_login_access.py` (least-privilege user creation), `IAM/get_all_iam_users.py`, `IAM/list_users.py`, `IAM/create_120users.py` (bounded bulk creation).
- **S3**: `file_from_s3.py`/`working_with_s3.py` to list buckets or objects.
- **STS**: `get_aws_account_id.py`, `test.py` (assume-role helper).

## Usage examples
- List EC2 instances tagged for prod backups:  
  `python list_instances.py --tag Prod=backup --state running --region us-east-1`
- Create snapshots for in-use backup volumes (wait for completion):  
  `python resource_ebs_snap.py --tag Prod=backup --wait`
- Audit IAM access keys older than 90 days and deactivate them:  
  `python access_keys.py --max-age-days 90 --action deactivate`
- Create a read-only IAM user with console access (password reset required):  
  `python create_an_iam_user_console_login_access.py my-user --create-login --password-reset-required`

> Note: `IAM/iam_users_info.py` contains sample CSV-style seed data for demos and is not executable code.
