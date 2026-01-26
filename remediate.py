import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DESIRED_PUBLIC_ACCESS_BLOCK = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def remediate(findings_report: Dict[str, Any], approve: bool) -> Dict[str, Any]:
    s3 = boto3.client("s3")

    findings: List[Dict[str, Any]] = findings_report.get("findings", [])
    targets = [f for f in findings if f.get("severity") == "CRITICAL"]

    actions: List[Dict[str, Any]] = []

    for f in targets:
        bucket = f.get("bucket")
        issue = f.get("issue")

        action = {
            "bucket": bucket,
            "issue": issue,
            "action": "put_public_access_block",
            "requested_config": DESIRED_PUBLIC_ACCESS_BLOCK,
            "status": "DRY_RUN" if not approve else "PENDING",
            "error": None,
        }

        if not bucket:
            action["status"] = "SKIPPED"
            action["error"] = "Missing bucket name in finding."
            actions.append(action)
            continue

        if not approve:
            actions.append(action)
            print(f"DRY RUN: Would enforce Block Public Access on [{bucket}]")
            continue

        try:
            s3.put_public_access_block(
                Bucket=bucket,
                PublicAccessBlockConfiguration=DESIRED_PUBLIC_ACCESS_BLOCK,
            )
            action["status"] = "APPLIED"
            print(f"APPLIED: Enforced Block Public Access on [{bucket}]")

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "Unknown")
            action["status"] = "FAILED"
            action["error"] = {"code": code, "message": e.response.get("Error", {}).get("Message")}
            print(f"FAILED: [{bucket}] ClientError: {code}")

        except Exception as e:
            action["status"] = "FAILED"
            action["error"] = str(e)
            print(f"FAILED: [{bucket}] {str(e)}")

        actions.append(action)

    return {
        "generated_at": now_utc_iso(),
        "service": "s3",
        "remediator": "aws-security-guard",
        "approve_mode": approve,
        "targets": len(targets),
        "actions": actions,
        "summary": {
            "applied": sum(1 for a in actions if a["status"] == "APPLIED"),
            "failed": sum(1 for a in actions if a["status"] == "FAILED"),
            "dry_run": sum(1 for a in actions if a["status"] == "DRY_RUN"),
            "skipped": sum(1 for a in actions if a["status"] == "SKIPPED"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Remediate CRITICAL S3 findings by enforcing Block Public Access.")
    parser.add_argument("--input", default="findings.json", help="Input findings JSON from scanner.")
    parser.add_argument("--output", default="remediation.json", help="Output remediation report JSON.")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Actually apply changes. If omitted, runs in dry-run mode.",
    )
    args = parser.parse_args()

    report = read_json(args.input)
    remediation_report = remediate(report, approve=args.approve)
    write_json(args.output, remediation_report)

    # Return non-zero only if we attempted apply and had failures.
    if args.approve and remediation_report["summary"]["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
