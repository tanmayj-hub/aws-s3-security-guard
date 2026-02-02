# AWS S3 Security Guard (Scanner + Remediation)

A lightweight AWS security automation project that:
- Scans S3 buckets for **public access misconfigurations**
- Produces **severity-based findings** (e.g., CRITICAL) in a JSON report
- Optionally remediates CRITICAL findings by enforcing **S3 Block Public Access**
- Verifies fixes by re-running the scanner

This repo includes a **production-style GitHub Actions integration** (scheduled scans + manual remediation with approvals).

**New (Add-on Module): Encryption AI Scanner**
- Invokes an AWS Lambda function (`s3-security-scanner`) to scan S3 bucket **encryption posture**
- Returns an AI-generated security summary (Gemini) plus raw per-bucket encryption results
- Runs automatically from the same scheduled GitHub Actions workflow (no EventBridge required)

---

## Start Here — Fork & Replicate (Recommended Order)

This repo contains **two scanners** (public-access + encryption AI) and **one remediation workflow**.  
If you’re forking this repo for the first time, follow this order so nothing “mysteriously fails”:

### 1) Read these files in this order
1. **Root `README.md`** (this file) — overall architecture + workflows + IAM
2. `iam/` — copy/paste policies for your AWS roles
3. `encryption-ai-scanner/README.md` — what the Lambda does
4. `encryption-ai-scanner/packaging-notes.md` — how to build/upload the Lambda ZIP (first-time deployment)

### 2) What you need to set up (high level)
1. **AWS IAM OIDC** (one-time per AWS account): lets GitHub Actions assume AWS roles securely (no long-lived keys).
2. **Two GitHub Actions roles** in AWS:
   - `SecurityGuardScanRole` (read-only + Lambda invoke)
   - `SecurityGuardRemediateRole` (write permissions to apply S3 Block Public Access)
3. **Encryption AI Lambda** deployed once in AWS:
   - Function name: `s3-security-scanner`
   - Execution role: `LambdaS3ScannerRole`
   - Env var: `GOOGLE_API_KEY` (Gemini)

### 3) Important: Why the Lambda role is separate from the GitHub Actions role
- **GitHub Actions role (`AWS_SCAN_ROLE_ARN`)**: assumed by GitHub Actions via OIDC to run the workflow and **invoke** Lambda.
- **Lambda execution role (`LambdaS3ScannerRole`)**: assumed by Lambda **at runtime** to call S3 APIs and CloudWatch Logs.

> Translation: GitHub Actions triggers Lambda — but Lambda runs using **its own** IAM role.

### 4) First-time replication checklist
✅ Create AWS OIDC provider → create roles → set GitHub secrets  
✅ Deploy the Lambda **once** (manual upload or via the optional “build ZIP” workflow below)  
✅ Enable encryption AI scanning in `.github/workflows/scan.yml` (toggle)  
✅ Run **S3 Security Scan** workflow (manual) → confirm artifacts upload

---

## Gemini API Key + Billing Setup (Required for AI Analysis)

The encryption scanner Lambda calls Gemini to generate the short AI security summary.  
To make that work, you need:
1) A **Gemini API key**
2) **Billing enabled** on the Google project behind that API key (otherwise you may get quota / 429 errors)

### Step A — Create a Gemini API key (Google AI Studio)
1. Open Google AI Studio: https://aistudio.google.com/
2. Sign in and create/select a project.
3. Generate an API key (“Get API key”).
4. Copy the key.

### Step B — Enable Billing (fixes `RESOURCE_EXHAUSTED` / quota issues)
1. Open Google Cloud Billing: https://console.cloud.google.com/billing
2. Add/link a billing account to the same project used in AI Studio.
3. Wait a few minutes, then re-test the Lambda.

### Step C — Store the API key in Lambda (best practice)
AWS Lambda → your function → **Configuration → Environment variables**:
- Key: `GOOGLE_API_KEY`
- Value: `<your Gemini API key>`

> Do **not** commit API keys into the repo.

---

## Tech Stack
- Python 3.12
- AWS S3 + IAM
- AWS Lambda (encryption scan add-on)
- GitHub Actions + OIDC (no static AWS keys)
- Optional: Cursor + AWS MCP for AI-assisted development

---

## Architecture

**Public Access Scan + Optional Remediation**
- `scanner.py` scans S3 public access configuration and outputs `findings.json`
- `remediate.py` enforces S3 Block Public Access on CRITICAL buckets
- GitHub Actions schedules scans and runs remediation only via manual approval

**Encryption AI Scan (Add-on)**
- GitHub Actions invokes `s3-security-scanner` Lambda
- Lambda checks bucket encryption and calls Gemini for an AI summary
- Results are logged to CloudWatch and returned to the workflow as an artifact

---

## GitHub Actions (Production-Style)

Workflows:
- `.github/workflows/scan.yml` — Scheduled scan (daily) + manual dispatch
- `.github/workflows/remediate.yml` — Manual remediation gated behind an Environment approval
- `.github/workflows/build-encryption-lambda-zip.yml` — Optional: build `s3_scanner.zip` in Actions (for users who don’t want local builds)

---

## 0) Create the Web Identity Provider in AWS (GitHub OIDC) — one-time per AWS account

You need GitHub OIDC so Actions can assume AWS roles without storing AWS access keys.

(Your existing OIDC steps remain the same.)

---

## 1) Create IAM roles in YOUR AWS account

You need two roles in AWS:
- `SecurityGuardScanRole` → used by scan workflow (read-only + optional Lambda invoke)
- `SecurityGuardRemediateRole` → used by remediation workflow (write permissions)

Policy files live under `iam/`.

---

## 2) Add GitHub Secrets in your repo

Repo → Settings → Secrets and variables → Actions:
- `AWS_SCAN_ROLE_ARN` = ARN of `SecurityGuardScanRole`
- `AWS_REMEDIATE_ROLE_ARN` = ARN of `SecurityGuardRemediateRole`

---

## 3) Add an approval gate for remediation (recommended)

GitHub repo → Settings → Environments:
- Create environment: `production`
- Add required reviewers

---

## 4) Deploy the Encryption AI Scanner Lambda (add-on)

This repo includes the Lambda source under:
- `encryption-ai-scanner/s3_scanner.py`
- `encryption-ai-scanner/README.md`
- `encryption-ai-scanner/packaging-notes.md`

### First-time deployment (important)
GitHub Actions can only **invoke** this Lambda — in a fresh fork, the Lambda does not exist yet.
Deploy it **once** in AWS before enabling the encryption scan step in the workflow.

**Option A (recommended): Build + upload locally**
- Follow `encryption-ai-scanner/packaging-notes.md` to create `s3_scanner.zip`
- Upload the ZIP in the Lambda console

**Option B (no local build): Build the ZIP using GitHub Actions**
- Run the workflow: `.github/workflows/build-encryption-lambda-zip.yml`
- Download the `s3_scanner.zip` artifact from the workflow run
- Upload the ZIP in the Lambda console

> After the Lambda exists, enable it in `.github/workflows/scan.yml` by setting `ENABLE_ENCRYPTION_AI_SCAN: "true"`.

**Lambda configuration:**
- Function name: `s3-security-scanner` (recommended)
- Runtime: Python 3.12
- Handler: `s3_scanner.lambda_handler`
- Timeout: 30 seconds
- Environment variable: `GOOGLE_API_KEY` = Gemini API key
- Execution role: `LambdaS3ScannerRole`

---

## 5) Run workflows

- Actions → **S3 Security Scan**
  - Confirms public access posture + uploads `findings.json`
  - (Optional) If `ENABLE_ENCRYPTION_AI_SCAN: "true"`, invokes the encryption Lambda and uploads `encryption_scan_response.json`

- Actions → **S3 Remediation (Manual)**

---

## Attribution

This repo combines learnings and implementations inspired by two guided projects from the NextWork **Security × AI** series:

- **Build an AI Security Guard for AWS** — focused on scanning S3 buckets for security misconfigurations (e.g., public access controls) and building a repeatable guard pattern.
- **AI Security Scanner for AWS S3** — focused on scanning S3 bucket encryption posture and generating AI-powered security insights (Gemini), including serverless Lambda deployment patterns.

If you want more project ideas like these, check out NextWork here: https://learn.nextwork.org/

On top of the NextWork baseline, this repo extends the ideas into a production-style workflow: scheduled scans, approval-gated remediation, and CI-friendly artifacts.