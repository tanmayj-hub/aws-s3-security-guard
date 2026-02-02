# Packaging Notes — encryption-ai-scanner (Lambda ZIP)

This module is deployed as an AWS Lambda function. Lambda runs in a Linux environment, so dependencies must be packaged as Linux-compatible wheels.

## What gets packaged
- `s3_scanner.py` (Lambda handler code)
- Python dependency:
  - `google-genai` (Gemini client SDK)

> Note: `boto3` is included in the AWS Lambda Python runtime by default, so it’s not typically bundled.

---

## Option A — Build locally (Windows PowerShell)

From repo root:

> Important: run these commands from the `encryption-ai-scanner/` folder (it contains the module `requirements.txt`).

```powershell
cd encryption-ai-scanner

Remove-Item -Recurse -Force package -ErrorAction SilentlyContinue
Remove-Item -Force s3_scanner.zip -ErrorAction SilentlyContinue

mkdir package

pip install --platform manylinux2014_x86_64 --target ./package --implementation cp --python-version 3.12 --only-binary=:all: -r requirements.txt

Copy-Item .\s3_scanner.py .\package\

Compress-Archive -Path .\package\* -DestinationPath .\s3_scanner.zip -Force
````

Upload `encryption-ai-scanner/s3_scanner.zip` to Lambda.

> macOS/Linux users: easiest path is Option B (build the zip using GitHub Actions). You can also build locally using standard `zip` commands if you prefer.

---

## Option B — Build ZIP using GitHub Actions (no local build)

If you don’t want to build locally:

1. Go to GitHub → Actions
2. Run: `.github/workflows/build-encryption-lambda-zip.yml`
3. Download the artifact (often named something like `s3_scanner_lambda_zip`)
4. Inside it, you’ll find `s3_scanner.zip` — upload that to AWS Lambda (Code → Upload from → .zip file)

---

## Lambda config checklist

* Runtime: Python 3.12
* Handler: `s3_scanner.lambda_handler`
* Timeout: 30 seconds
* Environment variables:

  * `GOOGLE_API_KEY` = Gemini API key
* Lambda execution role:

  * S3 permissions: list buckets + read encryption configuration
  * CloudWatch logging permissions (`AWSLambdaBasicExecutionRole`)

---

## Testing

Lambda console → Test with:

```json
{ "test": "manual-invoke" }
```

Expected:

* `statusCode: 200`
* `scan_results` array listing each bucket’s encryption status
* `ai_analysis` with a short security summary (requires valid API key + billing/quota enabled)