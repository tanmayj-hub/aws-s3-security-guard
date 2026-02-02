# Packaging Notes — Encryption AI Scanner Lambda

Lambda requires your code + dependencies bundled into a zip file (`s3_scanner.zip`).

## Option A — Build locally (recommended)

### 1) Create / activate venv (optional but recommended)
```bash
python -m venv venv
source venv/bin/activate     # macOS/Linux
# OR
venv\Scripts\activate        # Windows PowerShell
2) Install dependencies into a Lambda package folder
mkdir package
pip install --platform manylinux2014_x86_64 \
  --target ./package \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  -r requirements.txt
3) Add your code + zip it
cp s3_scanner.py package/
cd package
zip -r ../s3_scanner.zip .
cd ..
Upload s3_scanner.zip into AWS Lambda (Code → Upload from → .zip file).

Option B — Build via GitHub Actions (no local build)
If you don’t want to build locally, you can generate s3_scanner.zip using GitHub Actions:

Go to Actions → Build Encryption AI Scanner Lambda ZIP

Click Run workflow

Download the artifact: s3_scanner_lambda_zip

Upload s3_scanner.zip in the AWS Lambda console (Code → Upload from → .zip file)