# Deploying sefop-web to Oracle Cloud with automated CD

This is a step-by-step runbook for standing up a Continuous Deployment pipeline
that ships `sefop-web` to a free Oracle Cloud (OCI) VM automatically, every time
CI passes on `main`. No manual SSH session is needed after this is set up — a
merge to `main` alone triggers the deploy.

Every step below is tagged with who does it:

- **You** — something only you can do: browser clicks, payment info, account
  creation. Claude Code cannot do these for you.
- **Claude Code** — a terminal/SSH/git/file-editing step. Open a Claude Code
  session in this repo and ask it to do that step (you can paste the step
  number/description directly).

Follow the steps **in order** — later steps depend on earlier ones (e.g. you
need the VM's IP before Claude Code can SSH into it).

---

## Phase 0 — What you'll end up with

- One Oracle Cloud Free Tier ARM VM (2 OCPU / 12 GB), running Ubuntu 24.04.
- A domain, pointed at Cloudflare, with a Cloudflare Tunnel exposing
  `sefop.<yourdomain>` over HTTPS — no inbound ports open on the VM except SSH.
- `sefop-web`'s Docker image built and published to GitHub Container Registry
  (GHCR) automatically by GitHub Actions.
- A GitHub Actions workflow that: runs all 4 existing CI checks → builds and
  pushes the image → SSHes into the VM and swaps the running container for the
  new one, only if it passes a health check (old version keeps serving if the
  new one is broken).

Total ongoing cost: **US$0/month**, as long as you stay within OCI's Always
Free limits. The only recurring cost is the domain (~US$10/year) if you don't
already have one.

---

## Phase 1 — Oracle Cloud account and VM

### 1.1 Create the OCI account
**Responsible: You**

1. Go to `oracle.com/cloud/free` → *Start for free*.
2. Pick your **Home Region** carefully — it cannot be changed later, and this
   is where your Always Free resources will live. Prefer a region with 3
   Availability Domains (Ashburn, Phoenix, Frankfurt, London) for better ARM
   capacity, or a LATAM region (São Paulo, Santiago, Querétaro) if latency to
   you matters more — just confirm A1 shapes are available there first.
3. Card verification is required (a temporary ~US$1 hold, refunded) — you
   will not be charged as long as you stay on Free Tier / within Always Free
   limits.
4. Enable MFA when prompted. Note down your **tenancy name**.

### 1.2 Generate SSH keys
**Responsible: Claude Code**

Two separate keypairs are needed: one for you (interactive admin access), one
dedicated to the CD pipeline (deploy-only, more restricted). Ask Claude Code
to:

- Generate a personal keypair: `ssh-keygen -t ed25519 -C "oci-personal" -f ~/.ssh/oci_key`
- Generate a deploy keypair: `ssh-keygen -t ed25519 -C "oci-deploy" -f ~/.ssh/oci_deploy_key`
- Print both public keys so you can paste them into the OCI console in the
  next step.

### 1.3 Create the VM
**Responsible: You** (OCI console)

1. Console → ☰ Menu → Compute → Instances → *Create Instance*.
2. Name: `srv-sefop`.
3. Image: *Change image* → Ubuntu → **Canonical Ubuntu 24.04** (confirm it
   says aarch64/ARM).
4. Shape: *Change shape* → Ampere → `VM.Standard.A1.Flex` → 2 OCPUs / 12 GB
   RAM (this is the full pure-Free-Tier ARM allowance — no PAYG upgrade).
5. Networking: leave default (*Create new virtual cloud network*, public
   subnet, *Assign a public IPv4 address* checked).
6. Add SSH keys: *Paste public keys* → paste **both** public keys from step
   1.2 (`oci_key.pub` and `oci_deploy_key.pub`), one per line.
7. Boot volume: check *Specify a custom boot volume size* → 100 GB is plenty
   for a single VM within the 200 GB free allowance.
8. *Create*. Wait 1–2 minutes for it to reach `Running`. **Note the Public IP.**
9. If you hit "Out of host capacity": retry with a different Availability
   Domain, retry during US off-peak hours, or temporarily create a smaller
   shape (1 OCPU/6GB) and resize later via *Edit shape*.

### 1.4 Reserve the public IP
**Responsible: You** (OCI console)

The default public IP is ephemeral (changes if you ever recreate the
instance). Instance → *Attached VNICs* → *IPv4 Addresses* → *Edit* → switch
from *Ephemeral* to *Reserved public IP*. Free while assigned.

### 1.5 Set a budget alert
**Responsible: You** (OCI console)

Billing → Budgets → create a US$1 budget alert. If Oracle ever changes Always
Free terms, you find out by email, not by a surprise bill.

---

## Phase 2 — SSH access and base VM setup

### 2.1 Configure SSH aliases and verify connectivity
**Responsible: Claude Code**

Ask Claude Code to add this to `~/.ssh/config` (replace `<PUBLIC_IP>`):

```
Host sefop
    HostName <PUBLIC_IP>
    User ubuntu
    IdentityFile ~/.ssh/oci_key
```

Then verify: `ssh sefop "uname -a"`.

### 2.2 Base server setup
**Responsible: Claude Code** (over SSH, no manual server work)

Ask Claude Code to, on the `sefop` host:

1. Update packages, enable `unattended-upgrades` (security only).
2. Install Docker Engine + the Docker Compose plugin (official Docker apt
   repo, arm64 build).
3. Set timezone (ask which one you want — the original guide defaults to
   `America/Santiago`).
4. Harden SSH: disable password login and root login.
5. Leave OCI's iptables rules untouched — everything web-facing goes through
   Cloudflare Tunnel (Phase 4), so no new inbound ports are needed.

### 2.3 Create the restricted deploy user
**Responsible: Claude Code** (over SSH)

This is the account the CD pipeline will use — deliberately not `ubuntu`, and
deliberately **not** added to the `docker` group (group membership is
root-equivalent via the Docker socket, so it wouldn't actually restrict
anything). Ask Claude Code to:

1. Create a `deploy` user with no shell login password.
2. Add `oci_deploy_key.pub` to `deploy`'s `~/.ssh/authorized_keys`.
3. Add a `/etc/sudoers.d/deploy-docker` drop-in granting `deploy` NOPASSWD
   sudo access to only the exact `docker pull ...` / `docker compose ... up -d`
   / `docker compose ... down` invocations the deploy script needs — not
   blanket sudo, not full docker-group access.

Be aware this narrows, but doesn't perfectly sandbox, what a leaked deploy key
can do — flag this to yourself as a known, accepted tradeoff, not a solved
problem.

---

## Phase 3 — GitHub Container Registry

**Responsible: Claude Code** (repo changes; no manual registry setup needed —
GHCR is provisioned automatically the first time the workflow pushes to it)

1. This will be handled inside the CD workflow itself (Phase 5) — no separate
   account needed, since it uses the repo's own GitHub identity.
2. **After the first successful push** (i.e. once Phase 5 is live and has run
   once), go to the package at
   `github.com/orgs/sefop/packages/container/sefop-web/settings` and set
   visibility to **Public** — this is a one-time GitHub web UI action.
   **Responsible: You.**

---

## Phase 4 — Domain and Cloudflare Tunnel

### 4.1 Cloudflare account and domain
**Responsible: You** (payment required)

1. Sign up at `cloudflare.com`.
2. Buy a domain via Cloudflare Registrar (~US$10/year, at-cost pricing) —
   Domain Registration → Register a Domain.

### 4.2 Create the Tunnel
**Responsible: You** (dashboard clicks) **+ Claude Code** (server-side command)

1. You: Zero Trust → Networks → Tunnels → *Create a tunnel* → name it
   `srv-sefop`. Copy the connector token it gives you.
2. Claude Code (over SSH, using the token you paste in): install `cloudflared`
   on the VM from Cloudflare's official apt repo (arm64), run the connector
   command with your token, and enable it as a systemd service so it survives
   reboots.
3. You: in the same Tunnel's *Public Hostname* settings, add
   `sefop.<yourdomain>` → `http://localhost:8000`.
4. Claude Code: verify `https://sefop.<yourdomain>` is reachable (it won't
   return 200 yet — nothing is listening on port 8000 until Phase 6 — but it
   should show Cloudflare's SSL working, e.g. a 502 from Cloudflare, not a
   certificate error).

---

## Phase 5 — CD pipeline (this repo)

**Responsible: Claude Code** (all of this is code/config committed to the repo)

1. Add a `workflow_call:` trigger to each of the 4 existing CI workflow files
   (`ci-code-style.yml`, `ci-unit-tests.yml`, `ci-integration-tests.yml`,
   `ci-docker-build.yml`), alongside their existing `push`/`pull_request`
   triggers — so they can be reused as jobs.
2. Add `deploy/docker-compose.yml`: single `sefop-web` service, image
   `ghcr.io/sefop/sefop-web:latest`, port bound to `127.0.0.1:8000:8000` only,
   `restart: unless-stopped`.
3. Add `deploy/deploy.sh`: the actual swap logic —
   - `docker pull` the new `:<git-sha>`-tagged image.
   - Run it as a scratch container on a throwaway local port.
   - Poll `/health` with retries.
   - If healthy: update `docker-compose.yml`'s image tag, restart via
     `docker compose up -d`, remove the old container.
   - If unhealthy: remove the scratch container, exit non-zero — the
     previously-running container is left untouched, so the site stays up on
     the last good version.
4. Add `.github/workflows/cd-deploy.yml`:
   - Trigger: `push: branches: [main]`.
   - Jobs `code-style`, `unit-tests`, `integration-tests`, `docker-build`,
     each via `uses: ./.github/workflows/ci-*.yml`.
   - `build-and-push` job (`needs` all four above): builds the existing
     `Dockerfile`, tags `:latest` and `:${{ github.sha }}`, pushes to GHCR
     using the automatic `GITHUB_TOKEN`.
   - `deploy` job (`needs: build-and-push`): rsyncs `deploy/docker-compose.yml`
     and `deploy/deploy.sh` to the VM, then SSHes in as the `deploy` user
     (using the `DEPLOY_SSH_KEY` secret) and runs `deploy.sh`.
5. Set repo secrets via `gh secret set` (no browser needed):
   - `DEPLOY_SSH_KEY` — the private half of `oci_deploy_key`.
   - `DEPLOY_HOST` — the VM's reserved public IP.
6. Commit and open a PR so the new/changed workflow files themselves pass CI
   before merging to `main`.

**Optional, flagged but not required by this architecture** (deploy is
already gated on CI via `needs`, not branch protection): `main` currently has
no branch protection rule, so nothing stops a direct push that skips PR
review. Consider adding one. **Responsible: You** (repo Settings → Branches).

---

## Phase 6 — First deploy and verification

**Responsible: Claude Code**, with you watching the results

1. Merge the PR from Phase 5 to `main`.
2. Watch `cd-deploy.yml` run in the Actions tab: 4 CI jobs → `build-and-push`
   → `deploy`, all green.
3. Confirm `https://sefop.<yourdomain>/health` returns 200.
4. Deliberately break `/health` on a throwaway commit/branch to confirm the
   `deploy` job fails loudly and the site keeps serving the last good version
   — proving the rollback safety net actually works, not just that it's
   documented.
5. SSH in (`ssh sefop`) and confirm exactly one `sefop-web` container is
   running post-deploy — no leaked scratch containers from the health-check
   step.

---

## Quick reference: who does what, in order

| # | Step | Responsible |
|---|------|-------------|
| 1.1 | Create OCI account | You |
| 1.2 | Generate SSH keypairs | Claude Code |
| 1.3 | Create the VM | You |
| 1.4 | Reserve public IP | You |
| 1.5 | Set budget alert | You |
| 2.1 | SSH config + connectivity check | Claude Code |
| 2.2 | Base server setup (Docker, hardening) | Claude Code |
| 2.3 | Create restricted `deploy` user | Claude Code |
| 3 | GHCR (auto-provisioned) | — |
| 3 (after first push) | Set GHCR package public | You |
| 4.1 | Cloudflare account + buy domain | You |
| 4.2 | Create Tunnel + connect it | You + Claude Code |
| 5 | Write CD workflow, compose file, deploy script | Claude Code |
| 5 | Set GitHub secrets | Claude Code (via `gh secret set`) |
| 5 (optional) | Branch protection on `main` | You |
| 6 | Merge, watch pipeline, verify, test rollback | Claude Code + You |
