# Packaging Notes — encryption-ai-scanner (Lambda ZIP)

This module deploys as an AWS Lambda function. Lambda runs on Linux, so dependencies must be packaged as **Linux-compatible wheels**.

## What gets packaged
- `s3_scanner.py` (Lambda handler code)
- Python dependency:
  - `google-genai` (Gemini client SDK)

> `boto3` is already included in the AWS Lambda Python runtime, so it is not bundled here.

---

## Option A — Build locally (Windows PowerShell)

From repo root:

> Run these commands from `encryption-ai-scanner/` (it contains the module `requirements.txt`).

```powershell
cd encryption-ai-scanner

Remove-Item -Recurse -Force package -ErrorAction SilentlyContinue
Remove-Item -Force s3_scanner.zip -ErrorAction SilentlyContinue

mkdir package

pip install --platform manylinux2014_x86_64 --target ./package --implementation cp --python-version 3.12 --only-binary=:all: -r requirements.txt

Copy-Item .\\s3_scanner.py .\\package\\

Compress-Archive -Path .\\package\\* -DestinationPath .\\s3_scanner.zip -Force
````

Upload `encryption-ai-scanner/s3_scanner.zip` to Lambda.

---

## Option B — Build ZIP using GitHub Actions (no local build)

Workflow: `.github/workflows/build-encryption-lambda-zip.yml`

1. GitHub → Actions → run **Build Encryption AI Scanner Lambda ZIP**
2. Download the artifact (currently uploaded as: `s3_scanner_lambda_zip`)
3. **Extract the downloaded artifact ZIP**
4. Inside it, you’ll find the real Lambda deployment ZIP: `s3_scanner.zip`
5. Upload **that inner** `s3_scanner.zip` to AWS Lambda (Code → Upload from → .zip file)

### Why extraction is required

GitHub Actions artifacts are delivered as a wrapper ZIP. If you upload the wrapper ZIP directly, Lambda won’t see `s3_scanner.py` at the root and you’ll get:

* `Runtime.ImportModuleError: Unable to import module 's3_scanner'`

---

## Lambda config checklist

* Runtime: **Python 3.12**
* Handler: **`s3_scanner.lambda_handler`**
* Timeout: **30 seconds**
* Environment variables (optional):

  * `GOOGLE_API_KEY` = Gemini API key (AI summary is skipped if not set)
* Execution role:

  * S3 permissions: list buckets + read encryption configuration
  * CloudWatch logs permissions (e.g., `AWSLambdaBasicExecutionRole`)

> Console note: the Lambda inline editor may refuse to open large ZIPs (e.g., “file exceeds 3 MB”). This does **not** prevent deployment or execution.

---

## Testing

Lambda console → Test with:

```json
{ "trigger": "manual-invoke" }
```

Expected:

* `statusCode: 200`
* `body` contains JSON (as a string) with:

  * `scan_results` listing each bucket’s encryption status
  * `ai_analysis` (either a Gemini summary or a “skipped” message)
  * `alert` (`true` if any buckets are missing default encryption)