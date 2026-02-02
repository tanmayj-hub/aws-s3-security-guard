# encryption-ai-scanner (Lambda + Gemini)

An AWS Lambda-based scanner that:
1) Lists S3 buckets in your account
2) Checks server-side encryption configuration for each bucket
3) Uses Gemini to generate a short, actionable security assessment

This module complements the main repo’s S3 security guard by adding **encryption posture scanning + AI insights**.

---

## Start Here (Recommended Order)
1) Read the repo root `README.md` first (it explains the full pipeline + GitHub Actions + IAM).
2) Then read this file (module behavior and AWS setup).
3) Then follow `packaging-notes.md` to build and deploy the Lambda ZIP.

---

## What it scans
- **S3 server-side encryption**
  - Detects whether default encryption is enabled
  - Captures encryption type (e.g., `AES256`, `aws:kms`, or `None`)

---

## How it connects to the repo pipeline
- GitHub Actions can **invoke** this Lambda from `.github/workflows/scan.yml`
- Lambda runs using its own IAM execution role (`LambdaS3ScannerRole`)
- Results are returned to the workflow and uploaded as `encryption_scan_response.json`

> Note: GitHub Actions does not deploy this Lambda code by default. You deploy it once, then Actions invokes it.

---

## AWS setup (one-time)
### 1) Create the Lambda function
- Runtime: Python 3.12
- Function name: `s3-security-scanner` (recommended)
- Handler: `s3_scanner.lambda_handler`
- Timeout: 30 seconds

### 2) Add environment variable
- `GOOGLE_API_KEY` = your Gemini API key

### 3) IAM Role for Lambda (execution role)
Attach:
- Custom policy allowing:
  - `s3:ListAllMyBuckets`
  - `s3:GetEncryptionConfiguration`
- AWS managed policy:
  - `AWSLambdaBasicExecutionRole` (CloudWatch logging)

---

## Packaging and deployment
Follow: `packaging-notes.md`

Two ways to get `s3_scanner.zip`:
- Build locally (recommended) via pip + zip
- Or run `.github/workflows/build-encryption-lambda-zip.yml` to generate the ZIP as a GitHub Actions artifact

---

## Output format
The Lambda returns JSON like:

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

## Notes

* If Gemini billing/quota isn’t enabled, `ai_analysis` may return an API error message (S3 scan still succeeds).
* Keep API keys out of source control. Use Lambda environment variables (or AWS Secrets Manager/SSM for advanced setups).