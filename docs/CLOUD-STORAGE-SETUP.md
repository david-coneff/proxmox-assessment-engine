# Cloud Storage Setup Guide

**Document created:** 2026-05-31
**Review by:** 2027-05-31 (cloud provider UIs change; verify steps are current)

This guide covers setting up cloud storage credentials for use with broodforge's
backup system (restic + rclone). Each section walks through a specific provider.

Broodforge requires API-level access — not username + password — for all cloud
backup destinations. This is enforced during `setup-backup.py` configuration.

**Supported providers covered here:**
- [Google Drive](#google-drive) — OAuth2 or Service Account
- [Backblaze B2](#backblaze-b2) — Application Key (recommended first cloud option)
- [AWS S3](#aws-s3) — IAM user with access key
- [Cloudflare R2](#cloudflare-r2) — S3-compatible, no egress fees
- [Self-hosted MinIO](#self-hosted-minio) — S3-compatible, full local control

**If this document is more than 12 months old, treat the UI steps as approximate
and verify against the provider's current documentation.**

---

## Backblaze B2

*Recommended starting point for cloud backup — straightforward setup, competitive
pricing, no egress fees to Cloudflare Workers (relevant for R2 users), and restic
has native B2 support without rclone.*

**What you need:** A Backblaze account (free tier available for evaluation).
**Authentication:** Application Key (Key ID + Application Key string).
**Security note:** Application Keys can be scoped to a single bucket with specific
permissions. Always create a restricted key — not the Master Application Key.

### Step 1 — Create a Backblaze account

1. Go to [backblaze.com](https://www.backblaze.com) → Sign Up
2. Verify your email address

### Step 2 — Create a bucket

1. Log in → **B2 Cloud Storage** → **Buckets** → **Create a Bucket**
2. Bucket name: e.g. `broodforge-cell-a-backup` (must be globally unique)
3. Files in bucket: **Private** (not public)
4. Server-side encryption: **Enable** (SSE-B2 is free; adds a second encryption
   layer on top of restic's own encryption)
5. Note the bucket name — you will need it for rclone / restic configuration

### Step 3 — Create a restricted Application Key

1. **Account** → **App Keys** → **Add a New Application Key**
2. Name: `broodforge-backup` (descriptive, for your reference)
3. Allow access to bucket: select **the specific bucket you just created**
   (do NOT select "All Buckets")
4. Type of access: **Read and Write**
5. Allow List All Bucket Names: **No**
6. File name prefix: leave blank (or set to `restic/` if you want to restrict key
   to a specific path)
7. Click **Create New Key**
8. **Copy both the Key ID and the Application Key immediately** — the Application
   Key is shown only once. If you lose it, delete this key and create a new one.

### Step 4 — Configure in broodforge

When `setup-backup.py` prompts for a B2 destination, enter:

```
Provider: Backblaze B2
Key ID:   (paste the Key ID from step 3)
App Key:  (paste the Application Key from step 3)
Bucket:   broodforge-cell-a-backup
Path:     restic   (directory within the bucket for restic's repository)
```

Broodforge will initialise a restic repository at `b2:broodforge-cell-a-backup/restic`
and test the connection before saving the configuration.

---

## AWS S3

**What you need:** An AWS account.
**Authentication:** IAM user with an access key (not root account credentials).
**Security note:** Create a dedicated IAM user with a policy scoped to one bucket.
Never use root account credentials or an access key with broad permissions.

### Step 1 — Create an S3 bucket

1. AWS Console → **S3** → **Create bucket**
2. Bucket name: e.g. `broodforge-cell-a-backup` (globally unique; lowercase, hyphens only)
3. Region: choose a region geographically close to you
4. Block all public access: **enabled** (all four checkboxes)
5. Bucket versioning: optional; restic manages its own versioning
6. Server-side encryption: **Enable** — SSE-S3 (free) or SSE-KMS (requires KMS key)
7. Create bucket

### Step 2 — Create an IAM user with a scoped policy

1. AWS Console → **IAM** → **Users** → **Create user**
2. Username: `broodforge-backup`
3. Access type: **Programmatic access** (access key, not AWS Console login)
4. Permissions: attach a new inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::broodforge-cell-a-backup"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::broodforge-cell-a-backup/*"
    }
  ]
}
```

Replace `broodforge-cell-a-backup` with your actual bucket name.

5. Finish creating the user. On the final screen, copy the **Access Key ID** and
   **Secret Access Key** — the Secret Access Key is shown only once.

### Step 3 — Configure in broodforge

When `setup-backup.py` prompts for an S3 destination, enter:

```
Provider:        AWS S3
Region:          (your bucket's region, e.g. ap-southeast-2)
Access Key ID:   (paste from step 2)
Secret Key:      (paste from step 2)
Bucket:          broodforge-cell-a-backup
Path:            restic
```

---

## Cloudflare R2

*S3-compatible. No egress fees (you pay for storage and operations, not downloads).
A cost-effective option if you expect to restore frequently.*

**What you need:** A Cloudflare account with R2 enabled (requires credit card on file;
10 GB free per month, then ~$0.015/GB/month as of 2026).
**Authentication:** R2 API Token (not your Cloudflare account API key).

### Step 1 — Enable R2 on your Cloudflare account

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **R2** → **Get Started**
2. Enter a credit card if prompted (required even for free tier)

### Step 2 — Create an R2 bucket

1. **R2** → **Create bucket**
2. Bucket name: e.g. `broodforge-cell-a-backup`
3. Location: **Automatic** or choose a specific region
4. Create bucket

### Step 3 — Create a scoped API Token

1. **R2** → **Manage R2 API Tokens** → **Create API Token**
2. Token name: `broodforge-backup`
3. Permissions: **Object Read & Write**
4. Specify bucket: select **the specific bucket** you created (not all buckets)
5. TTL: **No expiration** (or set a rotation schedule and update broodforge when rotating)
6. Create token
7. Copy: **Access Key ID**, **Secret Access Key**, and note your **Account ID**
   (visible in the right sidebar of the R2 dashboard)
8. Your S3 endpoint is: `https://{Account ID}.r2.cloudflarestorage.com`

### Step 4 — Configure in broodforge

When `setup-backup.py` prompts for a Cloudflare R2 destination:

```
Provider:        Cloudflare R2 (S3-compatible)
Endpoint:        https://{your-account-id}.r2.cloudflarestorage.com
Access Key ID:   (paste from step 3)
Secret Key:      (paste from step 3)
Bucket:          broodforge-cell-a-backup
Path:            restic
```

Broodforge configures rclone with `type = s3`, `provider = Cloudflare`, and the
endpoint URL above.

---

## Google Drive

*The most complex provider to set up due to OAuth2 / Google Cloud project requirements.
Read all steps before starting — the Google Cloud Console UI changes frequently.*

**Two authentication options:**

| Option | Best for | Complexity |
|---|---|---|
| **OAuth2 (user account)** | Personal Google Drive; interactive setup | Medium |
| **Service Account** | Shared Drive / Google Workspace; non-interactive | Higher |

### Option A — OAuth2 (personal Google Drive)

OAuth2 tokens are tied to your Google account. You set them up interactively once;
rclone stores a refresh token that it uses automatically thereafter.

#### Step A.1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project selector at the top → **New Project**
3. Project name: `broodforge-backup` (internal name; users won't see it)
4. Create project

#### Step A.2 — Enable the Google Drive API

1. With your project selected: **APIs & Services** → **Library**
2. Search for `Google Drive API`
3. Click it → **Enable**

#### Step A.3 — Configure the OAuth consent screen

1. **APIs & Services** → **OAuth consent screen**
2. User type: **External** (unless you have a Google Workspace organisation)
3. App name: `broodforge-backup`
4. User support email: your email address
5. Developer contact: your email address
6. **Save and Continue** through Scopes (no scopes needed here) → **Save and Continue**
7. Add test users: add your own Google account email
8. **Save and Continue** → **Back to Dashboard**
9. Status will show "Testing" — this is fine for personal use (the app only
   needs to access your own Drive)

#### Step A.4 — Create OAuth 2.0 credentials

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Desktop app**
3. Name: `broodforge-rclone`
4. Create
5. Download the JSON file (or copy Client ID and Client Secret)

#### Step A.5 — Authorise rclone (run on the hatchery or your workstation)

```bash
# On a machine with a browser (your workstation, not the Proxmox host):
rclone config

# Follow the prompts:
# n) New remote
# name> gdrive
# Storage> drive                          (Google Drive)
# client_id>   (paste Client ID from step A.4)
# client_secret>   (paste Client Secret from step A.4)
# scope> drive                            (full access)
# root_folder_id>   (leave blank)
# service_account_file>   (leave blank)
# Edit advanced config? n
# Use auto config? y                      (opens browser for authorisation)
#   → Browser opens; log in as your Google account → Grant access
# Configure this as a Shared Drive? n
# Keep this remote? y
```

The resulting token is saved in `~/.config/rclone/rclone.conf`. Copy this file
to the Proxmox host at the same path.

#### Step A.6 — Configure in broodforge

```
Provider:      Google Drive (rclone remote)
rclone remote: gdrive
Path:          broodforge-backup/restic
```

Broodforge will use `rclone:gdrive:broodforge-backup/restic` as the restic backend.

---

### Option B — Service Account (Shared Drive / Workspace)

A service account is a Google identity for applications — no human OAuth flow,
no browser required. Better for production use, especially with Google Workspace.

#### Step B.1 — Create a project (same as A.1 and A.2 above)

#### Step B.2 — Create a Service Account

1. **IAM & Admin** → **Service Accounts** → **Create Service Account**
2. Name: `broodforge-backup`
3. Description: `restic backup agent for broodforge cluster`
4. Create and continue
5. Role: skip (no project-level role needed for Drive access)
6. Done

#### Step B.3 — Create and download a key

1. Click your new service account → **Keys** → **Add Key** → **Create new key**
2. Key type: **JSON**
3. Create — downloads a `.json` file. Store this securely; it is the service
   account's credential. Treat it like a private key — add it to KeePass.

#### Step B.4 — Share a Drive folder with the service account

1. In Google Drive, create a folder: `broodforge-backup`
2. Right-click → **Share**
3. Add the service account email (shown in Step B.2; looks like
   `broodforge-backup@your-project.iam.gserviceaccount.com`)
4. Role: **Editor**
5. Share

#### Step B.5 — Configure rclone with the service account

```bash
rclone config

# n) New remote
# name> gdrive-sa
# Storage> drive
# client_id>   (leave blank)
# client_secret>   (leave blank)
# scope> drive
# root_folder_id>   (leave blank, or paste the folder ID from the URL)
# service_account_file>   /path/to/service-account-key.json
# Edit advanced config? n
# Use auto config? n    (service account; no browser needed)
# Configure as Shared Drive? n   (unless using Google Workspace Shared Drive)
# y
```

#### Step B.6 — Configure in broodforge

```
Provider:      Google Drive (rclone remote — service account)
rclone remote: gdrive-sa
Path:          broodforge-backup/restic
```

---

## Self-Hosted MinIO

*S3-compatible object storage you run yourself. Zero cloud dependency; good for
operators who want the restic deduplication and encryption benefits without any
external service.*

**What you need:** A machine to run MinIO on (a spare node, a NAS, or even the
Proxmox host itself — though a separate machine is preferred for independence).

### Step 1 — Install MinIO

```bash
# On the MinIO host (Debian/Ubuntu):
wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio
chmod +x /usr/local/bin/minio

# Create data directory
mkdir -p /opt/minio/data

# Create a systemd unit (/etc/systemd/system/minio.service):
[Unit]
Description=MinIO Object Storage
After=network.target

[Service]
User=minio
Environment="MINIO_ROOT_USER=admin"
Environment="MINIO_ROOT_PASSWORD=change-me-on-first-run"
ExecStart=/usr/local/bin/minio server /opt/minio/data --console-address :9001
Restart=always

[Install]
WantedBy=multi-user.target

systemctl enable --now minio
```

### Step 2 — Access the MinIO console

Open `http://{minio-host}:9001` in your browser. Log in with the root credentials.

**Change the root password immediately** via **Identity** → **Users** → root account.
Use a readable passphrase (the broodforge format `Capital.word.phrase.9` is suitable).

### Step 3 — Create a bucket and access key

1. **Buckets** → **Create Bucket**
   - Name: `broodforge-backup`
   - Versioning: off (restic manages versioning)
   - Object locking: off

2. **Access Keys** → **Create Access Key**
   - Name: `broodforge-backup`
   - Copy Access Key and Secret Key
   - Restrict to your bucket if MinIO version supports bucket-scoped keys

### Step 4 — Configure in broodforge

```
Provider:        MinIO (S3-compatible)
Endpoint:        http://{minio-host}:9000    (use https if TLS is configured)
Access Key ID:   (from step 3)
Secret Key:      (from step 3)
Bucket:          broodforge-backup
Path:            restic
```

MinIO is configured as an S3-compatible provider in rclone with `provider = Minio`
and `endpoint = http://{minio-host}:9000`.

---

## Keeping This Document Current

Cloud provider UIs and API processes change. This document should be reviewed:
- When a provider announces a console or API change
- When a setup step produces a different screen than described
- On an annual schedule (date at top of document)

To update: edit this file, update the date at the top, and commit to Forgejo.
The assessment engine does not monitor this file for staleness — it is a manual
maintenance responsibility.

If you encounter a step that has changed significantly, open an issue in the
broodforge Forgejo repository with the updated steps so other operators benefit.
