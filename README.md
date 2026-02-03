# AWS S3 Security Guard (Scanner + Remediation)

A lightweight AWS security automation repo that helps you catch and fix common S3 security risks *before they turn into incidents*.

### Real-world problems this solves
- **Prevents accidental data exposure** from misconfigured S3 public access settings (a common source of leaks).
- Replaces manual “check S3 settings in console” audits with **repeatable, scheduled security checks**.
- Adds an optional **encryption posture scan** with an AI-generated summary to speed up review and reporting.
- Supports teams that want a simple security gate in CI/CD: **scan → fail on critical findings → remediate with approval → verify**.

This repo includes a **production-style GitHub Actions integration** (scheduled scans + manual remediation with approvals).

**New (Add-on Module): Encryption AI Scanner**
- Invokes an AWS Lambda function (`s3-security-scanner`) to scan S3 bucket **encryption posture**
- Returns an AI-generated security summary (Gemini) plus raw per-bucket encryption results
- Runs as its **own workflow** (no EventBridge required)

---

## Tech Stack
- **Python 3.12**
- **boto3 / botocore** (AWS SDK for Python)
- **AWS S3**
- **GitHub Actions**
- **AWS IAM + GitHub OIDC** (no long-lived AWS keys)
- **AWS Lambda** (encryption scanner add-on)
- **Gemini API (google-genai)** (AI analysis inside the Lambda)

---

## Architecture

### GitHub Actions pipeline (Scan + Remediate + Encryption AI Scan)

```mermaid
flowchart LR
  classDef box fill:#1f2937,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef store fill:#111827,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef gate fill:#374151,stroke:#f59e0b,color:#ffffff,stroke-width:1px;

  A1["Public Access Scan\n(scan-public-access.yml)\ncron + manual"]:::box
  A3["Encryption Scan (AI)\n(scan-encryption-ai.yml)\ncron + manual"]:::box
  A2["Remediate Workflow\n(remediate.yml)\nmanual dispatch"]:::box
  GATE["Approval Gate\nEnvironment production"]:::gate

  F1["Artifact\ns3-findings\n(findings.json)"]:::store
  F3["Artifact\ns3-encryption-ai-scan\n(encryption_scan_response.json)"]:::store
  F2["Artifacts\ns3-findings-before • s3-remediation-report • s3-findings-after"]:::store

  L1["Lambda\ns3-security-scanner\n(encryption + AI)"]:::box

  A1 -->|"run scanner.py\nupload findings\nfail if CRITICAL"| F1
  A3 -->|"invoke Lambda\nupload response"| L1 --> F3

  A2 -->|"baseline scan → remediate → verify"| F2
  A2 --> GATE -->|"approved"| A2a["apply remediation\napprove=true"]:::box
  A2a -->|"upload reports"| F2
````

### AWS side (OIDC → STS → IAM Roles → S3 + Lambda)

```mermaid
flowchart LR
  classDef box fill:#1f2937,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef store fill:#111827,stroke:#9ca3af,color:#ffffff,stroke-width:1px;

  OIDC["OIDC Provider\n(token.actions.githubusercontent.com)"]:::box
  STS["STS\nAssumeRoleWithWebIdentity"]:::box

  RSCAN["IAM Role\nSecurityGuardScanRole\nread only (+ invoke Lambda)"]:::box
  RREM["IAM Role\nSecurityGuardRemediateRole\nwrite"]:::box

  LAMBDA["Lambda\ns3-security-scanner"]:::box
  LROLE["IAM Role\nLambdaS3ScannerRole\nS3 encryption read + logs"]:::box

  S3["S3\nBuckets"]:::store
  AI["Gemini API\n(GOOGLE_API_KEY)"]:::store

  OIDC --> STS
  STS --> RSCAN
  STS --> RREM

  RSCAN -->|"List buckets\nGet public access block"| S3
  RREM -->|"Put public access block"| S3

  RSCAN -->|"InvokeFunction"| LAMBDA
  LAMBDA --> LROLE
  LROLE -->|"List buckets\nGet encryption config"| S3
  LAMBDA -->|"AI analysis (optional)"| AI
```

---

## Optional (Learning Mode): Cursor + AWS MCP

This project was initially developed following a guided workflow using **Cursor + AWS MCP**.

**What it was used for:**

* Quickly creating test S3 buckets and misconfigurations for validation
* Running AWS actions through natural language (“fix critical S3 buckets”) during learning

**Do you need it for production/GitHub Actions?**
No — the production pipeline in this repo runs using **Python scripts + GitHub Actions + AWS OIDC**. Cursor/MCP is optional and not required to replicate the automation.

---

## Start Here — Fork & Replicate (Recommended Order)

This repo contains:

* **Scanner #1:** Public access misconfig scan (GitHub Actions runs `scanner.py`)
* **Remediation:** Manual + approval-gated remediation (via `remediate.py`)
* **Scanner #2 (Optional Add-on):** Encryption posture + AI analysis (AWS Lambda, invoked by Actions)

### Choose your path

* **Minimal setup (fastest):** Public access scan + optional remediation (no Lambda / no Gemini)
* **Full setup:** Add encryption Lambda + Gemini AI summary + scheduled encryption workflow

### 1) Read these files in this order

1. **Root `README.md`** (this file)
2. `iam/` — trust policy template + IAM permissions policies
3. `encryption-ai-scanner/README.md` — encryption Lambda behavior + AWS setup
4. `encryption-ai-scanner/packaging-notes.md` — build/upload Lambda ZIP (first-time deployment)

### 2) First-time replication checklist

✅ Create AWS OIDC provider → create roles → set GitHub secrets
✅ Run **S3 Public Access Scan** (manual) → confirm `s3-findings` artifact contains `findings.json`
✅ (Optional) Deploy encryption Lambda once → run **S3 Encryption Scan (AI via Lambda)** → confirm `s3-encryption-ai-scan` artifact uploads
✅ Run **S3 Remediation (Manual)** in dry-run → review report → apply only when ready

---

## Gemini API Key + Billing Setup (Required for AI Analysis)

The encryption scanner Lambda calls Gemini to generate a short AI security summary.

To make AI analysis work, you need:

1. A **Gemini API key**
2. **Billing enabled** on the Google project behind that API key (otherwise you may see quota / 429 errors)

### Step A — Create a Gemini API key (Google AI Studio)

1. Open Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
2. Sign in and create/select a project
3. Generate an API key (“Get API key”)
4. Copy the key

### Step B — Enable Billing (fixes `RESOURCE_EXHAUSTED` / quota issues)

1. Open Google Cloud Billing: [https://console.cloud.google.com/billing](https://console.cloud.google.com/billing)
2. Add/link a billing account to the same project used in AI Studio
3. Wait a few minutes, then re-test the Lambda

### Step C — Store the API key in Lambda (best practice)

AWS Lambda → your function → **Configuration → Environment variables**:

* Key: `GOOGLE_API_KEY`
* Value: `<your Gemini API key>`

> Do **not** commit API keys into the repo.

---

## GitHub Actions (Production-Style)

### Workflows

#### 1) Public Access Scan

* **`.github/workflows/scan-public-access.yml`**

  * Scheduled daily scan + manual trigger
  * Runs public access scan via `scanner.py` (uploads `findings.json`)
  * Fails when CRITICAL public access findings exist

**Inputs (manual run):**

* `allow_buckets` (optional): comma-separated allowlist of buckets to scan

**Output:**

* Artifact: `s3-findings` → `findings.json`

#### 2) Encryption Scan (AI via Lambda)

* **`.github/workflows/scan-encryption-ai.yml`**

  * Scheduled daily + manual trigger
  * Invokes the encryption scanner Lambda and uploads the response

**Inputs (manual run):**

* `function_name` (required): Lambda name or full ARN (default: `s3-security-scanner`)
* `payload` (optional): JSON string payload (default is fine)
* `fail_on_alert` (optional): `true` to fail the workflow if Lambda returns `alert=true`

**Prerequisites:**

* Lambda function `s3-security-scanner` deployed in the same region as the workflow (repo defaults to `us-east-1`)
* GitHub scan role must have `lambda:InvokeFunction` on that Lambda
* (Optional) `GOOGLE_API_KEY` set in Lambda env for AI summary

**Output:**

* Artifact: `s3-encryption-ai-scan` → `encryption_scan_response.json`

#### 3) Remediation (Manual)

* **`.github/workflows/remediate.yml`**

  * Manual trigger only
  * Runs: baseline scan → remediate (dry-run unless approved) → verification scan
  * Recommended behind a GitHub Environment approval gate

**Inputs:**

* `approve`: `true` to apply changes (default is dry-run)
* `allow_buckets` (optional): only target these buckets (useful for testing)
* `exclude_buckets` (optional): comma-separated buckets to exclude from remediation + verification

**Important behavior:**

* Scan reports **all** buckets (visibility is complete).
* Exclusions affect **remediation and verification only**.

**Outputs:**

* Artifacts: `s3-findings-before`, `s3-remediation-report`, `s3-findings-after`

#### 4) Build Encryption Lambda ZIP (Optional Helper)

* **`.github/workflows/build-encryption-lambda-zip.yml`**

  * Builds `encryption-ai-scanner/s3_scanner.zip` as a GitHub Actions artifact:

    * Artifact name: `s3_scanner_lambda_zip`

> Important: GitHub Actions artifacts download as a wrapper ZIP.
> Extract the downloaded artifact, then upload the **inner** `s3_scanner.zip` to Lambda.
> See `encryption-ai-scanner/packaging-notes.md`.

---

# Replication Steps (Fork-friendly)

## 0) Create the Web Identity Provider in AWS (GitHub OIDC) — one-time per AWS account

AWS Console → **IAM** → **Identity providers** → **Add provider**

* Provider type: **OpenID Connect**
* Provider URL: `https://token.actions.githubusercontent.com`
* Audience: `sts.amazonaws.com`

✅ After this is created, you can select **Trusted entity type → Web identity** when creating IAM roles.

---

## 1) Create IAM roles in YOUR AWS account

Create two roles:

* `SecurityGuardScanRole` (read-only scan + Lambda invoke)
* `SecurityGuardRemediateRole` (applies S3 Block Public Access)

Use:

* Trust policy template: `iam/github-oidc-trust-policy-template.json`
* Permissions policies:

  * `iam/scan-role-policy.json`
  * `iam/remediate-role-policy.json`

> Note: `iam/scan-role-policy.json` may include a placeholder `<AWS_ACCOUNT_ID>` for the Lambda ARN. Replace it with your account id (and confirm region + function name).

---

## 2) Add GitHub Secrets in your repo

GitHub repo → Settings → Secrets and variables → Actions → **Secrets**:

* `AWS_SCAN_ROLE_ARN` = `arn:aws:iam::<AWS_ACCOUNT_ID>:role/SecurityGuardScanRole`
* `AWS_REMEDIATE_ROLE_ARN` = `arn:aws:iam::<AWS_ACCOUNT_ID>:role/SecurityGuardRemediateRole`

---

## 3) Add an approval gate for remediation (recommended)

GitHub repo → Settings → Environments:

* Create environment: `production`
* Add required reviewers

---

## 4) Deploy the Encryption AI Scanner Lambda (optional add-on)

See:

* `encryption-ai-scanner/README.md`
* `encryption-ai-scanner/packaging-notes.md`

After deploying the Lambda, run:

* Actions → **S3 Encryption Scan (AI via Lambda)**

> There is no toggle anymore. Encryption scanning is a separate workflow that assumes the Lambda exists.

---

## 5) Run workflows

### A) Public access scan
Actions → **S3 Public Access Scan**
- Uploads `findings.json` (artifact: `s3-findings`)
- Fails if CRITICAL findings exist (expected security gate behavior)

### B) Encryption scan (optional add-on)
Actions → **S3 Encryption Scan (AI via Lambda)**
- Invokes the Lambda encryption scanner (default: `s3-security-scanner`)
- Uploads `encryption_scan_response.json` (artifact: `s3-encryption-ai-scan`)
- Optional: set `fail_on_alert=true` to fail the run if Lambda returns `alert=true`

> Prerequisite: Deploy the Lambda once (see `encryption-ai-scanner/README.md` and `encryption-ai-scanner/packaging-notes.md`).

### C) Remediation (manual)
Actions → **S3 Remediation (Manual)**
- Start with `approve=false` (dry-run)
- Use `exclude_buckets` to skip buckets you do not want modified
- Set `approve=true` only when ready
- Uploads: `s3-findings-before`, `s3-remediation-report`, `s3-findings-after`

## Re-enable daily scheduled runs (optional)

By default, the scan workflows are **manual-only** to avoid consuming resources.

To re-enable daily cron schedules:
1. Open:
   - `.github/workflows/scan-public-access.yml`
   - `.github/workflows/scan-encryption-ai.yml`
2. Find the commented block under `on:`:
   ```yaml
   # schedule:
   #  - cron: "..."
Uncomment the schedule: lines.

Commit and push.

---

## Common errors (quick fixes)

### Encryption workflow fails with `ResourceNotFoundException`

* Your Lambda is in a different region than the workflow.
* Fix: deploy Lambda in the same region as the workflow (repo defaults to `us-east-1`) or update the workflow region.

### Lambda test fails with `No module named 's3_scanner'`

* You likely uploaded the **artifact wrapper zip** instead of the inner Lambda zip.
* Fix: extract the downloaded artifact and upload the **inner** `s3_scanner.zip`.

---

## Attribution

This repo combines learnings and implementations inspired by two guided projects from the NextWork **Security × AI** series:

* **Build an AI Security Guard for AWS** — focused on scanning S3 buckets for security misconfigurations (e.g., public access controls) and building a repeatable guard pattern.
* **AI Security Scanner for AWS S3** — focused on scanning S3 bucket encryption posture and generating AI-powered security insights (Gemini), including serverless Lambda deployment patterns.
If you want more project ideas like these, check out NextWork here: https://learn.nextwork.org/

On top of the NextWork baseline, this repo extends the ideas into a production-style workflow: scheduled scans, approval-gated remediation, and CI-friendly artifacts.