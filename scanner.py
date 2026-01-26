import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_csv_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    items = [x.strip() for x in value.split(",") if x.strip()]
    return items or None


def should_scan_bucket(bucket_name: str, allow_buckets: Optional[List[str]]) -> bool:
    if not allow_buckets:
        return True
    return bucket_name in allow_buckets


def get_public_access_block_config(s3, bucket_name: str) -> Dict[str, Any]:
    """
    Returns PublicAccessBlockConfiguration dict.
    Raises ClientError if missing or access denied.
    """
    resp = s3.get_public_access_block(Bucket=bucket_name)
    return resp["PublicAccessBlockConfiguration"]


def evaluate_public_access_block(config: Dict[str, Any]) -> bool:
    """
    Returns True if all 4 protections are enabled.
    """
    return all(
        [
            config.get("BlockPublicAcls") is True,
            config.get("IgnorePublicAcls") is True,
            config.get("BlockPublicPolicy") is True,
            config.get("RestrictPublicBuckets") is True,
        ]
    )


def scan_s3_buckets(allow_buckets: Optional[List[str]] = None) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    findings: List[Dict[str, Any]] = []

    print("Scanning S3 buckets for public access...\n")

    buckets = s3.list_buckets()
    bucket_list = buckets.get("Buckets", [])
    print(f"Found {len(bucket_list)} buckets (before filtering)\n")

    scanned_count = 0

    for bucket in bucket_list:
        bucket_name = bucket["Name"]

        if not should_scan_bucket(bucket_name, allow_buckets):
            continue

        scanned_count += 1

        try:
            config = get_public_access_block_config(s3, bucket_name)

            if not evaluate_public_access_block(config):
                findings.append(
                    {
                        "bucket": bucket_name,
                        "issue": "Public access not fully blocked",
                        "severity": "CRITICAL",
                    }
                )
                print(f"CRITICAL: [{bucket_name}] Public access not fully blocked")
            else:
                print(f"[OK]     [{bucket_name}] Public access properly blocked")

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "Unknown")
            if code == "NoSuchPublicAccessBlockConfiguration":
                findings.append(
                    {
                        "bucket": bucket_name,
                        "issue": "No public access block configured",
                        "severity": "CRITICAL",
                    }
                )
                print(f"CRITICAL: [{bucket_name}] No public access block configured")
            else:
                # For production you might want to record ACCESS_DENIED as HIGH, etc.
                findings.append(
                    {
                        "bucket": bucket_name,
                        "issue": f"Could not scan bucket (ClientError: {code})",
                        "severity": "HIGH",
                        "details": e.response.get("Error", {}),
                    }
                )
                print(f"ERROR:   [{bucket_name}] ClientError: {code}")

        except Exception as e:
            findings.append(
                {
                    "bucket": bucket_name,
                    "issue": f"Could not scan bucket (Exception)",
                    "severity": "HIGH",
                    "details": str(e),
                }
            )
            print(f"ERROR:   [{bucket_name}] {str(e)}")

    report: Dict[str, Any] = {
        "generated_at": now_utc_iso(),
        "service": "s3",
        "scanner": "aws-security-guard",
        "scanned_buckets": scanned_count,
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "CRITICAL"),
            "high": sum(1 for f in findings if f.get("severity") == "HIGH"),
            "medium": sum(1 for f in findings if f.get("severity") == "MEDIUM"),
            "low": sum(1 for f in findings if f.get("severity") == "LOW"),
        },
    }

    print("\n" + "=" * 55)
    if len(findings) == 0:
        print("[OK] No security issues found! All scanned buckets are configured.")
    else:
        print(f"Found {len(findings)} security issue(s):")
        for f in findings:
            print(f"  [{f['severity']}] {f['bucket']}: {f['issue']}")
    print("=" * 55)

    return report


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan S3 buckets for public access misconfigurations.")
    parser.add_argument("--output", default="findings.json", help="Path to write JSON findings.")
    parser.add_argument("--allow-buckets", default=None, help="Comma-separated allowlist of bucket names.")
    parser.add_argument(
        "--fail-on",
        default="CRITICAL",
        choices=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Exit non-zero if findings at/above this severity exist. Use NONE to never fail.",
    )
    args = parser.parse_args()

    allow_buckets = parse_csv_list(args.allow_buckets)
    report = scan_s3_buckets(allow_buckets=allow_buckets)
    write_json(args.output, report)

    threshold = SEVERITY_ORDER[args.fail_on]
    if threshold == 0:
        return 0

    worst = 0
    for f in report["findings"]:
        worst = max(worst, SEVERITY_ORDER.get(f.get("severity", "NONE"), 0))

    # Convention:
    # 0 = clean, 2 = findings, 1 = runtime error (we don't use 1 here because we record errors as HIGH findings)
    if worst >= threshold and report["summary"]["total_findings"] > 0:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
