# Packaging Notes — encryption-ai-scanner (Lambda ZIP)

This module is deployed as an AWS Lambda function. Lambda runs in a Linux environment, so when building the deployment ZIP on Windows, dependencies must be installed as Linux-compatible wheels.

## What gets packaged
- `s3_scanner.py` (Lambda handler code)
- Python dependencies required by the scanner:
  - `google-genai` (Gemini client SDK)

> Note: `boto3` is available in the AWS Lambda Python runtime by default, so we don’t bundle it in the ZIP unless there’s a specific need to pin a newer version.

---

## Windows (PowerShell) — Build `s3_scanner.zip`

From the repo root:

```powershell
cd encryption-ai-scanner

Remove-Item -Recurse -Force package -ErrorAction SilentlyContinue
Remove-Item -Force s3_scanner.zip -ErrorAction SilentlyContinue

mkdir package

# Install Linux-compatible wheels for Lambda
pip install --platform manylinux2014_x86_64 --target ./package --implementation cp --python-version 3.12 --only-binary=:all: google-genai

# Add Lambda code
Copy-Item .\s3_scanner.py .\package\

# Create deployment zip
Compress-Archive -Path .\package\* -DestinationPath .\s3_scanner.zip -Force
````

Upload `encryption-ai-scanner/s3_scanner.zip` to Lambda.

---

## Lambda config checklist

* Runtime: Python 3.12
* Handler: `s3_scanner.lambda_handler`
* Environment variables:

  * `GOOGLE_API_KEY` = Gemini API key
* IAM role attached to the Lambda:

  * S3 permissions: list buckets + read encryption configuration
  * CloudWatch Logs permissions

---

## Testing

Use Lambda console → Test with:

```json
{ "test": "manual-invoke" }
```

Expected:

* `statusCode: 200`
* `scan_results` array listing each bucket’s encryption status
* `ai_analysis` with a short security summary (requires valid API key + billing/quota enabled)

````
