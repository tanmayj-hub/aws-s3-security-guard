# AWS S3 Security Guard (Scanner + Remediation)

A lightweight AWS security automation project that:
- Scans S3 buckets for **public access misconfigurations**
- Produces **severity-based findings** (e.g., CRITICAL) in a JSON report
- Optionally remediates CRITICAL findings by enforcing **S3 Block Public Access**
- Verifies fixes by re-running the scanner

This repo includes a **production-style GitHub Actions integration** (scheduled scans + manual remediation with approvals).

---

## Tech Stack
- **Python 3.12**
- **boto3 / botocore** (AWS SDK for Python)
- **AWS S3**
- **GitHub Actions**
- **AWS IAM + GitHub OIDC** (no long-lived AWS keys)

---

## Optional (Learning Mode): Cursor + AWS MCP
This project was initially developed following a guided workflow using **Cursor + AWS MCP**.

**What it was used for:**
- Quickly creating test S3 buckets and misconfigurations for validation
- Running AWS actions through natural language (“fix critical S3 buckets”) during learning

**Do you need it for production/GitHub Actions?**
No — the production pipeline in this repo runs using **Python scripts + GitHub Actions + AWS OIDC**. Cursor/MCP is optional and not required to replicate the automation.

---

## Local Setup (Windows PowerShell)

```md
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
  * Uploads `findings.json` as an artifact
  * Fails the run when **CRITICAL** findings exist (intended “security gate” behavior)

* **`.github/workflows/remediate.yml`**

  * Manual trigger only
  * Runs: scan → remediate → re-scan verification
  * `approve=false` = dry-run, `approve=true` = apply changes
  * Recommended: keep remediation behind an approval gate via GitHub Environments

### Important: no ARNs in the repo

To keep this repo fork-friendly (and avoid exposing account-specific ARNs), workflows read role ARNs from **GitHub Secrets**:

* `AWS_SCAN_ROLE_ARN`
* `AWS_REMEDIATE_ROLE_ARN`

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

## 4) Run workflows

* Actions → **S3 Security Scan**
* Actions → **S3 Remediation (Manual)**

---

## Attribution

This project was completed as part of a guided learning workflow from **NextWork - Build an AI Security Guard for AWS** and extended with:

* Production-style GitHub Actions pipeline
* OIDC-based AWS auth (no long-lived AWS keys)
* Controlled remediation workflow (approval gate + verification scan)
* Fork-friendly setup (role ARNs stored in GitHub Secrets)
