import boto3
import json
import os

from google import genai


def lambda_handler(event, context):
    """Scan S3 buckets for encryption and use AI to explain risks"""

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("Scanning S3 buckets for encryption...")

    # Get all S3 buckets
    response = s3_client.list_buckets()
    buckets = response.get("Buckets", [])

    print(f"Found {len(buckets)} buckets to scan\n")

    scan_results = []

    for bucket in buckets:
        bucket_name = bucket["Name"]

        # Check if bucket has encryption enabled
        encrypted = False
        encryption_type = "None"

        try:
            enc = s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])

            if rules:
                algo = (
                    rules[0]
                    .get("ApplyServerSideEncryptionByDefault", {})
                    .get("SSEAlgorithm")
                )
                if algo:
                    encrypted = True
                    encryption_type = algo
        except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
            encrypted = False
            encryption_type = "None"
        except Exception as e:
            # Don't fail the whole scan if one bucket errors
            encrypted = False
            encryption_type = f"Error: {type(e).__name__}"
            print(f"Error checking encryption for {bucket_name}: {e}")

        scan_results.append(
            {
                "bucket_name": bucket_name,
                "encrypted": encrypted,
                "encryption_type": encryption_type,
            }
        )

        status = "Encrypted" if encrypted else "Not Encrypted"
        print(f"{status}: {bucket_name} ({encryption_type})")

    # Count unencrypted buckets
    unencrypted = [r for r in scan_results if not r["encrypted"]]
    unencrypted_count = len(unencrypted)
    unencrypted_buckets = [r["bucket_name"] for r in unencrypted]

    print("\nAnalyzing security findings with Gemini AI...")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        ai_analysis = "AI analysis skipped: GOOGLE_API_KEY not configured"
    else:
        try:
            client = genai.Client(api_key=api_key)

            prompt = f"""You are an AWS security expert. Analyze this S3 encryption scan and provide a brief security assessment.

Scan Results:
- Total Buckets: {len(buckets)}
- Encrypted: {len(buckets) - unencrypted_count}
- Unencrypted: {unencrypted_count}
- Unencrypted Bucket Names: {', '.join(unencrypted_buckets) if unencrypted_buckets else 'None'}

Provide a 2-3 sentence analysis:
1. What's the security risk of unencrypted buckets?
2. What encryption should be enabled? (AES256 or aws:kms)
3. What action should the user take immediately?

Be concise and actionable."""
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            ai_analysis = resp.text

        except Exception as e:
            ai_analysis = f"AI analysis failed: {str(e)}"

    result = {
        "total_buckets": len(buckets),
        "unencrypted_buckets": unencrypted_count,
        "encrypted_buckets": len(buckets) - unencrypted_count,
        "scan_results": scan_results,
        "ai_analysis": ai_analysis,
        "alert": unencrypted_count > 0,
    }

    print(f"\nScan complete: {unencrypted_count}/{len(buckets)} buckets need encryption")

    return {"statusCode": 200, "body": json.dumps(result)}
