# encryption-ai-scanner

An AWS Lambda-based scanner that:
1) Lists S3 buckets in your account
2) Checks server-side encryption configuration for each bucket
3) Uses Gemini to generate a short, actionable security assessment

This module complements the main repo’s S3 security guard by adding **encryption posture scanning + AI insights**.

---

## What it scans
- **S3 server-side encryption**
  - Detects whether each bucket has default encryption enabled
  - Captures encryption type (e.g., `AES256`, `aws:kms`, or `None`)

---

## How it works (high level)
1) Lambda runs `s3_scanner.lambda_handler`
2) Uses `boto3` to:
   - `s3:ListAllMyBuckets`
   - `s3:GetEncryptionConfiguration`
3) Builds a scan summary and sends it to Gemini for analysis
4) Returns JSON with:
   - total/encrypted/unencrypted counts
   - per-bucket scan results
   - `ai_analysis` text
   - `alert` boolean (true if unencrypted buckets exist)

---

## AWS setup (one-time)
### 1) Lambda
- Runtime: Python 3.12
- Function name: `s3-security-scanner` (recommended)
- Handler: `s3_scanner.lambda_handler`
- Timeout: 30s

### 2) Environment variable
- `GOOGLE_API_KEY` = your Gemini API key

### 3) IAM Role for Lambda
Attach policies:
- Custom policy allowing:
  - `s3:ListAllMyBuckets`
  - `s3:GetEncryptionConfiguration`
- AWS managed policy:
  - `AWSLambdaBasicExecutionRole` (CloudWatch logging)

---

## Packaging and deployment
See: `packaging-notes.md`

---

## GitHub Actions integration (repo-level)
This repo’s scheduled scan workflow can invoke this Lambda and store results as an artifact.

The scan workflow needs permission to invoke the Lambda:
- `lambda:InvokeFunction` on the Lambda ARN

Once enabled, the workflow:
- runs the existing public access scan (security gate)
- invokes this Lambda for encryption posture + AI analysis
- uploads both outputs as build artifacts

---

## Output example
The Lambda returns:

```json
{
  "total_buckets": 7,
  "unencrypted_buckets": 0,
  "encrypted_buckets": 7,
  "scan_results": [
    { "bucket_name": "example", "encrypted": true, "encryption_type": "AES256" }
  ],
  "ai_analysis": "Short security summary...",
  "alert": false
}
````

---

## Notes / Known behaviors

* If Gemini quota/billing isn’t enabled, `ai_analysis` may return an API error message (S3 scan still succeeds).
* Lambda includes `boto3` by default; we typically only bundle `google-genai` in the ZIP.

```