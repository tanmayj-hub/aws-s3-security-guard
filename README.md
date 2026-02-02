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
- Can run from the same GitHub Actions workflow (no EventBridge required)

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

### GitHub Actions pipeline (Scan + Remediate + Optional Encryption AI Scan)

```mermaid
flowchart LR
  classDef box fill:#1f2937,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef store fill:#111827,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef gate fill:#374151,stroke:#f59e0b,color:#ffffff,stroke-width:1px;

  A1["Scan Workflow\ncron + manual"]:::box
  A2["Remediate Workflow\nmanual dispatch"]:::box
  GATE["Approval Gate\nEnvironment production"]:::gate

  F1["Artifact\nfindings.json"]:::store
  F3["Artifact\nencryption_scan_response.json"]:::store
  F2["Artifacts\nbefore.json • remediation.json • after.json"]:::store

  L1["Lambda\ns3-security-scanner\n(encryption + AI)"]:::box

  A1 -->|"run scanner.py\nupload findings\nfail if CRITICAL"| F1
  A1 -->|"optional: invoke Lambda\n(ENABLE_ENCRYPTION_AI_SCAN=true)"| L1 --> F3

  A2 -->|"baseline scan"| F2
  A2 --> GATE -->|"approved"| A2a["apply remediation\napprove=true\nverify scan"]:::box
  A2a -->|"upload reports"| F2
````

### AWS side (OIDC → STS → IAM Roles → S3 + Lambda)

```mermaid
flowchart LR
  classDef box fill:#1f2937,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef store fill:#111827,stroke:#9ca3af,color:#ffffff,stroke-width:1px;

  OIDC["OIDC Provider\n(token.actions.githubusercontent.com)"]:::box
  STS["STS\nAssumeRoleWithWebIdentity"]:::box

  RSCAN["IAM Role\nSecurityGuardScanRole\nread only (+ optional invoke)"]:::box
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

  RSCAN -->|"Optional: InvokeFunction"| LAMBDA
  LAMBDA --> LROLE
  LROLE -->|"List buckets\nGet encryption config"| S3
  LAMBDA -->|"AI analysis"| AI
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
* **Full setup:** Add encryption Lambda + Gemini AI summary + optional Lambda invocation from scans

### 1) Read these files in this order

1. **Root `README.md`** (this file)
2. `iam/` — trust policy template + IAM permissions policies
3. `encryption-ai-scanner/README.md` — encryption Lambda behavior + AWS setup
4. `encryption-ai-scanner/packaging-notes.md` — build/upload Lambda ZIP (first-time deployment)

### 2) First-time replication checklist

✅ Create AWS OIDC provider → create roles → set GitHub secrets
✅ Run **S3 Security Scan** workflow (manual) → confirm `findings.json` artifact
✅ (Optional) Deploy encryption Lambda once → enable encryption scan toggle → confirm second artifact uploads

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

* **`.github/workflows/scan.yml`**

  * Scheduled daily scan + manual trigger
  * Runs public access scan via `scanner.py` (uploads `findings.json`)
  * Optionally invokes encryption Lambda and uploads `encryption_scan_response.json`
  * Fails when CRITICAL public access findings exist

* **`.github/workflows/remediate.yml`**

  * Manual trigger only
  * Runs: scan → remediate → re-scan verification
  * Recommended behind a GitHub Environment approval gate

* **`.github/workflows/build-encryption-lambda-zip.yml`** (optional helper)

  * Builds `encryption-ai-scanner/s3_scanner.zip` as an Actions artifact for users who don’t want local builds

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

* `SecurityGuardScanRole` (read-only scan + optional Lambda invoke)
* `SecurityGuardRemediateRole` (applies S3 Block Public Access)

Use:

* Trust policy template: `iam/github-oidc-trust-policy-template.json`
* Permissions policies:

  * `iam/scan-role-policy.json`
  * `iam/remediate-role-policy.json`

> Note: `iam/scan-role-policy.json` includes a placeholder `<AWS_ACCOUNT_ID>` for the Lambda ARN. Replace it with your account id (and confirm region + function name).

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

After deploying the Lambda, enable invocation in `.github/workflows/scan.yml`:

* `ENABLE_ENCRYPTION_AI_SCAN: "true"`

---

## 5) Run workflows

Actions → **S3 Security Scan**

* Uploads `findings.json`
* If enabled, uploads `encryption_scan_response.json`

Actions → **S3 Remediation (Manual)**

---

## Attribution

This repo combines learnings and implementations inspired by two guided projects from the NextWork **Security × AI** series:

* **Build an AI Security Guard for AWS** — focused on scanning S3 buckets for security misconfigurations (e.g., public access controls) and building a repeatable guard pattern.
* **AI Security Scanner for AWS S3** — focused on scanning S3 bucket encryption posture and generating AI-powered security insights (Gemini), including serverless Lambda deployment patterns.

If you want more project ideas like these, check out NextWork here: [https://learn.nextwork.org/](https://learn.nextwork.org/)

On top of the NextWork baseline, this repo extends the ideas into a production-style workflow: scheduled scans, approval-gated remediation, and CI-friendly artifacts.
