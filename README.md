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
- Can run from the same GitHub Actions workflow (no EventBridge required)

---

## Start Here — Fork & Replicate (Recommended Order)

This repo contains:
- **Scanner #1:** Public access misconfig scan (runs in GitHub Actions via `scanner.py`)
- **Remediation:** Manual + approval-gated remediation (via `remediate.py`)
- **Scanner #2 (Add-on):** Encryption posture + AI analysis (runs in AWS Lambda, invoked by GitHub Actions)

If you’re forking for the first time, follow this exact order so nothing “mysteriously fails”.

### 1) Read these files in this order
1. **Root `README.md`** (this file) — full setup + workflows + architecture
2. `iam/` — trust policy template + IAM permissions policies
3. `encryption-ai-scanner/README.md` — what the Lambda module does + how it connects
4. `encryption-ai-scanner/packaging-notes.md` — how to build/upload the Lambda ZIP (first-time deployment)

### 2) What you need to set up (high level)
1. **AWS IAM OIDC** (one-time per AWS account): lets GitHub Actions assume AWS roles securely (no static keys)
2. **Two GitHub Actions roles** in AWS:
   - `SecurityGuardScanRole` (read-only + optional Lambda invoke)
   - `SecurityGuardRemediateRole` (write permissions to apply S3 Block Public Access)
3. **Encryption AI Lambda deployed once in AWS** (only if you enable the add-on):
   - Function name: `s3-security-scanner`
   - Execution role: `LambdaS3ScannerRole`
   - Env var: `GOOGLE_API_KEY` (Gemini API key)

### 3) Important: Why the Lambda role is separate from the GitHub Actions role
- **GitHub Actions role (`AWS_SCAN_ROLE_ARN`)**: assumed by GitHub Actions via OIDC to run the workflow and optionally **invoke** Lambda.
- **Lambda execution role (`LambdaS3ScannerRole`)**: assumed by Lambda **at runtime** to read S3 encryption settings and write CloudWatch logs.

> Translation: GitHub Actions triggers Lambda — but Lambda runs using its own IAM role.

### 4) First-time replication checklist (recommended)
✅ Create AWS OIDC provider → create roles → set GitHub secrets  
✅ Run **S3 Security Scan** workflow (manual) → confirm `findings.json` artifact  
✅ (Optional) Deploy the encryption Lambda once → enable encryption scan toggle → confirm second artifact uploads

---

## Gemini API Key + Billing Setup (Required for AI Analysis)

The encryption scanner Lambda calls Gemini to generate a short AI security summary.

To make AI analysis work, you need:
1) A **Gemini API key**
2) **Billing enabled** on the Google project behind that API key (otherwise you may see quota / 429 errors)

### Step A — Create a Gemini API key (Google AI Studio)
1. Open Google AI Studio: https://aistudio.google.com/
2. Sign in and create/select a project
3. Generate an API key (“Get API key”)
4. Copy the key

### Step B — Enable Billing (fixes `RESOURCE_EXHAUSTED` / quota issues)
1. Open Google Cloud Billing: https://console.cloud.google.com/billing
2. Add/link a billing account to the same project used in AI Studio
3. Wait a few minutes, then re-test the Lambda

### Step C — Store the API key in Lambda (best practice)
AWS Lambda → your function → **Configuration → Environment variables**:
- Key: `GOOGLE_API_KEY`
- Value: `<your Gemini API key>`

> Do **not** commit API keys into the repo.

---

## Tech Stack
- **Python 3.12**
- **boto3 / botocore** (AWS SDK for Python)
- **AWS S3**
- **GitHub Actions**
- **AWS IAM + GitHub OIDC** (no long-lived AWS keys)
- **AWS Lambda** (encryption scanner add-on)
- **Gemini API (google-genai / google-genai client)** (AI analysis inside the Lambda)

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

## Local Setup (Windows PowerShell)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
aws configure
python scanner.py --output findings.json --fail-on CRITICAL
```

---

## GitHub Actions (Production-Style)

### Workflows

* **`.github/workflows/scan.yml`**

  * Scheduled daily scan + manual trigger
  * Runs **Public access scan** via `scanner.py` (uploads `findings.json`)
  * Optionally invokes **Encryption AI scan** Lambda `s3-security-scanner` (uploads `encryption_scan_response.json`)
  * Fails the run when **CRITICAL** public access findings exist (intended “security gate” behavior)

  **Note about the encryption scan:**

  * Fresh forks won’t have the Lambda deployed yet, so encryption scan is designed to be **optional**
  * Enable it after deployment by setting `ENABLE_ENCRYPTION_AI_SCAN: "true"` in `scan.yml`

* **`.github/workflows/remediate.yml`**

  * Manual trigger only
  * Runs: scan → remediate → re-scan verification
  * `approve=false` = dry-run, `approve=true` = apply changes
  * Recommended: keep remediation behind an approval gate via GitHub Environments

* **`.github/workflows/build-encryption-lambda-zip.yml`** (optional helper)

  * Builds `encryption-ai-scanner/s3_scanner.zip` as a GitHub Actions artifact
  * Useful for people who don’t want to build ZIPs locally
  * You still upload the ZIP into AWS Lambda once (first-time deployment)

### Important: no ARNs in the repo

To keep this repo fork-friendly (and avoid exposing account-specific ARNs), workflows read role ARNs from **GitHub Secrets**:

* `AWS_SCAN_ROLE_ARN`
* `AWS_REMEDIATE_ROLE_ARN`

> The Gemini API key is stored as a **Lambda environment variable** (`GOOGLE_API_KEY`), not in GitHub.

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

### 1A) Create role using Web Identity

For each role:

1. AWS Console → IAM → Roles → **Create role**
2. Trusted entity type: **Web identity**
3. Identity provider: `token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. Continue → create role (attach permissions next)

### 1B) Trust policy (Web Identity)

Use `iam/github-oidc-trust-policy-template.json` as a template and replace placeholders:

* `<AWS_ACCOUNT_ID>` = your AWS account id
* `OWNER/REPO` = your GitHub repo fork (e.g., `yourname/aws-s3-security-guard`)
* Branch is `main`

### 1C) Permissions policies

This repo provides ready-to-use policies in `/iam/`:

* Scan role policy: `iam/scan-role-policy.json`
* Remediate role policy: `iam/remediate-role-policy.json`

Scan Role requires:

* `s3:ListAllMyBuckets`
* `s3:GetBucketPublicAccessBlock`
* (Optional add-on) `lambda:InvokeFunction` to invoke `s3-security-scanner`

Remediate Role requires:

* same as scan role, plus `s3:PutBucketPublicAccessBlock`

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

## 4) Deploy the Encryption AI Scanner Lambda (add-on)

This repo includes the Lambda source under:

* `encryption-ai-scanner/s3_scanner.py`
* `encryption-ai-scanner/README.md`
* `encryption-ai-scanner/packaging-notes.md`

### First-time deployment (important)

GitHub Actions can only **invoke** this Lambda. In a fresh fork, the Lambda does not exist yet.
Deploy it **once** in AWS before enabling encryption scan in the workflow.

**Option A (recommended): Build + upload locally**

* Follow `encryption-ai-scanner/packaging-notes.md` to create `s3_scanner.zip`
* Upload the ZIP in the Lambda console

**Option B (no local build): Build the ZIP using GitHub Actions**

* Run the workflow: `.github/workflows/build-encryption-lambda-zip.yml`
* Download the `s3_scanner.zip` artifact
* Upload it in the Lambda console

After the Lambda exists:

* Set `ENABLE_ENCRYPTION_AI_SCAN: "true"` in `.github/workflows/scan.yml`

**Lambda configuration:**

* Function name: `s3-security-scanner` (recommended)
* Runtime: Python 3.12
* Handler: `s3_scanner.lambda_handler`
* Timeout: 30 seconds
* Environment variable: `GOOGLE_API_KEY` = Gemini API key
* Execution role: `LambdaS3ScannerRole`

---

## 5) Run workflows

Actions → **S3 Security Scan**

* Public access scan runs and uploads `findings.json`
* If enabled, encryption scan invokes Lambda and uploads `encryption_scan_response.json`

Actions → **S3 Remediation (Manual)**

* Manual remediation with approval gate

---

## Attribution

This repo combines learnings and implementations inspired by two guided projects from the NextWork **Security × AI** series:

* **Build an AI Security Guard for AWS** — focused on scanning S3 buckets for security misconfigurations (e.g., public access controls) and building a repeatable guard pattern.
* **AI Security Scanner for AWS S3** — focused on scanning S3 bucket encryption posture and generating AI-powered security insights (Gemini), including serverless Lambda deployment patterns.

If you want more project ideas like these, check out NextWork here: [https://learn.nextwork.org/](https://learn.nextwork.org/)

On top of the NextWork baseline, this repo extends the ideas into a production-style workflow: scheduled scans, approval-gated remediation, and CI-friendly artifacts.