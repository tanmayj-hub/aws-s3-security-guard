# AWS S3 Security Guard (Scanner + Remediation)

A lightweight AWS security automation project that:
- Scans all S3 buckets for **public access misconfigurations**
- Produces **severity-based findings** (e.g., CRITICAL) in a JSON report
- Optionally remediates CRITICAL findings by enforcing **S3 Block Public Access**
- Verifies fixes by re-running the scanner

This repo also includes a **production-style GitHub Actions integration** (scheduled scans + manual remediation with approvals).

---

## Tech Stack
- **Python 3.12**
- **boto3 / botocore** (AWS SDK for Python)
- **AWS S3**
- **GitHub Actions**
- **AWS IAM + GitHub OIDC** (no long-lived AWS keys)

---

## What the Scanner Checks
For each bucket, the scanner validates the 4 S3 Block Public Access controls:
- `BlockPublicAcls`
- `IgnorePublicAcls`
- `BlockPublicPolicy`
- `RestrictPublicBuckets`

If the Public Access Block config is missing or incomplete, it reports a **CRITICAL** finding.

---

## Local Setup

### 1) Create and activate a venv (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
````

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure AWS credentials (local)

```powershell
aws configure
```

### 4) Run the scanner

```powershell
python scanner.py --output findings.json --fail-on CRITICAL
```

### 5) Remediate (dry-run)

```powershell
python remediate.py --input findings.json --output remediation.json
```

### 6) Remediate (apply changes)

```powershell
python remediate.py --input findings.json --approve --output remediation.json
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
  * Supports `approve=true` to apply changes
  * Recommended: keep remediation behind an approval gate via GitHub Environments

### Secure AWS Auth (OIDC)

This repo is designed to use **GitHub OIDC → AWS IAM Roles**:

* `SecurityGuardScanRole` (read-only)
* `SecurityGuardRemediateRole` (write: PutBucketPublicAccessBlock)

Update the role ARNs in workflows to match your AWS account.

---

## Safety Notes

* Remediation defaults to **dry-run** unless explicitly approved.
* Use an allowlist for testing so you only modify your test bucket.

---

## Attribution

This project was completed as part of a guided learning workflow from **NextWork**.
I extended it for a production-style GitHub setup by adding:

* GitHub Actions scheduled scanning
* OIDC-based AWS auth (no long-lived keys)
* Controlled remediation workflow (manual approval + verification scan)
* Reproducible repo structure and documentation
