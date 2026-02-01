````md
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

  A1["Scan Workflow\ncron + manual"]:::box
  A2["Remediate Workflow\nmanual dispatch"]:::box
  GATE["Approval Gate\nEnvironment production"]:::gate

  F1["Artifact\nfindings.json"]:::store
  F3["Artifact\nencryption_scan_response.json"]:::store
  F2["Artifacts\nbefore.json • remediation.json • after.json"]:::store

  L1["Lambda\ns3-security-scanner\n(encryption + AI)"]:::box

  A1 -->|"run scanner.py\nupload findings\nfail if CRITICAL"| F1
  A1 -->|"invoke Lambda\nupload response"| L1 --> F3

  A2 -->|"baseline scan"| F2
  A2 --> GATE -->|"approved"| A2a["apply remediation\napprove true\nverify scan"]:::box
  A2a -->|"upload reports"| F2
````

### AWS side (OIDC → STS → IAM Roles → S3 + Lambda)

```mermaid
flowchart LR
  classDef box fill:#1f2937,stroke:#9ca3af,color:#ffffff,stroke-width:1px;
  classDef store fill:#111827,stroke:#9ca3af,color:#ffffff,stroke-width:1px;

  OIDC["OIDC Provider\n(token.actions.githubusercontent.com)"]:::box
  STS["STS\nAssumeRoleWithWebIdentity"]:::box

  RSCAN["IAM Role\nSecurityGuardScanRole\nread only"]:::box
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
  * Runs two checks:

    * **Public access scan** via `scanner.py` (uploads `findings.json`)
    * **Encryption AI scan** by invoking Lambda `s3-security-scanner` (uploads `encryption_scan_response.json`)
  * Fails the run when **CRITICAL** public access findings exist (intended “security gate” behavior)

* **`.github/workflows/remediate.yml`**

  * Manual trigger only
  * Runs: scan → remediate → re-scan verification
  * `approve=false` = dry-run, `approve=true` = apply changes
  * Recommended: keep remediation behind an approval gate via GitHub Environments

### Important: no ARNs in the repo

To keep this repo fork-friendly (and avoid exposing account-specific ARNs), workflows read role ARNs from **GitHub Secrets**:

* `AWS_SCAN_ROLE_ARN`
* `AWS_REMEDIATE_ROLE_ARN`

> The Gemini API key is stored as a **Lambda environment variable** (`GOOGLE_API_KEY`), not in GitHub.

---

# Replication Steps (Fork-friendly)

## 0) Create the Web Identity Provider in AWS (GitHub OIDC) — one-time per AWS account

This is what enables the **“Web identity”** option when you create IAM roles for GitHub Actions.

AWS Console → **IAM** → **Identity providers** → **Add provider**

* Provider type: **OpenID Connect**
* Provider URL: `https://token.actions.githubusercontent.com`
* Audience: `sts.amazonaws.com`

✅ After this is created, you will be able to select **Trusted entity type → Web identity** when creating roles.

---

## 1) Create IAM roles in YOUR AWS account

Create two roles:

* `SecurityGuardScanRole` (read-only scan)
* `SecurityGuardRemediateRole` (applies S3 Block Public Access)

### 1A) Create role using Web Identity

For **each** role:

1. AWS Console → IAM → Roles → **Create role**
2. Trusted entity type: **Web identity**
3. Identity provider: `token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. Continue → create the role (you’ll attach permissions next)

### 1B) Trust policy (Web Identity)

After role creation, update the trust policy to this (replace placeholders):

* `<AWS_ACCOUNT_ID>` = your AWS account id
* `OWNER/REPO` = your GitHub repo (fork), e.g. `yourname/aws-s3-security-guard`
* Branch is `main`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### 1C) Permissions policies (copy-paste)

This repo provides ready-to-use IAM policies in `/iam/`:

* Scan role policy: `iam/scan-role-policy.json`
* Remediate role policy: `iam/remediate-role-policy.json`

Attach them to the roles as inline policies or managed policies.

**Scan Role requires:**

* `s3:ListAllMyBuckets`
* `s3:GetBucketPublicAccessBlock`
* `lambda:InvokeFunction` (to invoke the encryption scanner Lambda)

**Remediate Role requires:**

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

**Lambda configuration:**

* Function name: `s3-security-scanner` (recommended)
* Runtime: Python 3.12
* Handler: `s3_scanner.lambda_handler`
* Timeout: 30 seconds
* Environment variable:

  * `GOOGLE_API_KEY` = your Gemini API key

**Lambda IAM Role:**

* Create a role like `LambdaS3ScannerRole` with:

  * `s3:ListAllMyBuckets`
  * `s3:GetEncryptionConfiguration`
  * `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

> Note: Gemini access requires billing/quota enabled on the Google project used by your API key.

---

## 5) Run workflows

* Actions → **S3 Security Scan**

  * Confirms public access posture + uploads `findings.json`
  * Invokes the encryption Lambda + uploads `encryption_scan_response.json`

* Actions → **S3 Remediation (Manual)**

---

## Attribution

This repo combines learnings and implementations inspired by two guided projects from the NextWork **Security × AI** series:

- **Build an AI Security Guard for AWS** — focused on scanning S3 buckets for security misconfigurations (e.g., public access controls) and building a repeatable guard pattern.
- **AI Security Scanner for AWS S3** — focused on scanning S3 bucket encryption posture and generating AI-powered security insights (Gemini), including serverless Lambda deployment patterns.

On top of the NextWork baseline, this repo extends the ideas into a production-style workflow with:
- GitHub Actions automation (scheduled scans + manual remediation)
- AWS IAM + GitHub OIDC (no long-lived AWS keys)
- Approval-gated remediation with verification scans
- A modular structure that keeps both scanners under one security automation pipeline

If you want more hands-on project ideas in the same style (Security × AI × AWS), check out NextWork here: https://learn.nextwork.org/

```
::contentReference[oaicite:0]{index=0}
```
