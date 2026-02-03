# encryption-ai-scanner (Lambda + Gemini)

An AWS Lambda-based scanner that:

1) Lists S3 buckets in your account  
2) Checks **default server-side encryption** configuration per bucket  
3) (Optional) Uses **Gemini** to generate a short, actionable security assessment

This module complements the repo’s public-access guard by adding **encryption posture scanning + AI insights**.

---

## Start here (recommended order)
1. Read the repo root `README.md` first (overall pipeline + IAM + workflows).
2. Read this file (module behavior + AWS setup).
3. Follow `packaging-notes.md` (build + deploy the Lambda ZIP).

---

## What it scans
- **S3 default encryption**
  - Detects whether default encryption is enabled
  - Captures encryption type (e.g., `AES256`, `aws:kms`, or `None`)

---

## How it connects to the repo pipeline

### GitHub Actions workflow
- Workflow file: `.github/workflows/scan-encryption-ai.yml`
- What it does:
  - Assumes the scan role via OIDC (`AWS_SCAN_ROLE_ARN`)
  - Invokes this Lambda (default function name: `s3-security-scanner`)
  - Uploads the Lambda response as an artifact: `encryption_scan_response.json`

> GitHub Actions does **not** deploy this Lambda code. You deploy it once, then Actions invokes it.

### Lambda execution role
The Lambda runs under its own execution role (separate from the GitHub scan role). That role needs:
- `s3:ListAllMyBuckets`
- `s3:GetEncryptionConfiguration`
- CloudWatch logs permissions (e.g., `AWSLambdaBasicExecutionRole`)

---

## AWS setup (one-time)

### 1) Create the Lambda function
Recommended defaults (match the workflow defaults):
- **Region:** keep consistent with your workflows (repo defaults to `us-east-1`)
- **Runtime:** Python 3.12
- **Function name:** `s3-security-scanner`
- **Handler:** `s3_scanner.lambda_handler`
- **Timeout:** 30 seconds

### 2) Package + deploy code
Follow: `packaging-notes.md`

You will upload: `encryption-ai-scanner/s3_scanner.zip`

### 3) Optional: enable Gemini AI analysis
Set Lambda environment variable:
- `GOOGLE_API_KEY` = your Gemini API key

If `GOOGLE_API_KEY` is not set, the scan still runs and returns results, but AI output will be:
- `AI analysis skipped: GOOGLE_API_KEY not configured`

---

## Output format

This Lambda returns a **Lambda proxy-style** response:

```json
{
  "statusCode": 200,
  "body": "{...json string...}"
}
````

The JSON inside `body` looks like:

```json
{
  "total_buckets": 7,
  "unencrypted_buckets": 0,
  "encrypted_buckets": 7,
  "scan_results": [
    { "bucket_name": "example", "encrypted": true, "encryption_type": "AES256" }
  ],
  "ai_analysis": "Short security summary (or skipped)...",
  "alert": false
}
```

The GitHub Actions workflow prints the raw response in logs and uploads it as an artifact.

---

## Notes

* If Gemini billing/quota isn’t enabled, `ai_analysis` may contain an API error message (the S3 scan can still succeed).
* Keep API keys out of source control. Prefer Lambda environment variables (or Secrets Manager / SSM for advanced setups).