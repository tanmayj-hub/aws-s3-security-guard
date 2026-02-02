# Encryption AI Scanner (S3) — Lambda + Gemini

This module scans all S3 buckets in your AWS account, checks whether default bucket encryption is enabled, and generates a short, actionable AI security summary using Gemini.

## What it does
- Lists S3 buckets
- Checks bucket encryption configuration (AES256 vs aws:kms vs none)
- Returns:
  - per-bucket encryption status
  - a concise AI recommendation summary

## Files
- `s3_scanner.py` — Lambda handler and scan logic
- `requirements.txt` — dependencies for the Lambda package
- `packaging-notes.md` — packaging instructions (local + GitHub Actions)

---

## Deployment (first-time)

This module must be deployed as an AWS Lambda function **once** before it can be invoked by GitHub Actions.

You have two ways to produce the deployment ZIP (`s3_scanner.zip`):

- **Option A (recommended): build locally** — follow `packaging-notes.md`
- **Option B (no local build): build in GitHub Actions** — run `.github/workflows/build-encryption-lambda-zip.yml` and download the artifact

After uploading the ZIP to AWS Lambda, configure:
- Runtime: Python 3.12
- Handler: `s3_scanner.lambda_handler`
- Timeout: 30 seconds
- Environment variable: `GOOGLE_API_KEY`

Then enable the optional step in `.github/workflows/scan.yml`:
- `ENABLE_ENCRYPTION_AI_SCAN: "true"`
