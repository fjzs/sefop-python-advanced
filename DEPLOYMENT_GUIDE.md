# Deploying sefop-web to Render with automated CD

> **Note on the pivot:** this guide originally targeted a self-managed Oracle
> Cloud (OCI) VM. After repeatedly hitting "Out of host capacity" errors on
> OCI's free ARM tier across all availability domains, we switched to
> [Render](https://render.com) — a PaaS that builds directly from this repo's
> existing `Dockerfile` and eliminates VM provisioning, SSH, and Cloudflare
> Tunnel entirely. The SSH keypairs generated earlier
> (`~/.ssh/oci_key`, `~/.ssh/oci_deploy_key`) are unused by this path — no
> OCI VM was actually created, so there's nothing to clean up there.

Every step below is tagged with who does it:

- **You** — browser clicks, account creation, DNS/payment. Claude Code
  cannot do these for you.
- **Claude Code** — a terminal/git/file-editing step. Open a Claude Code
  session in this repo and ask it to do that step.

Follow the steps **in order**.

---

## Phase 0 — What you'll end up with

- A Render Web Service running `sefop-web`, built straight from this repo's
  `Dockerfile` — no VM to patch, harden, or provision capacity for.
- A custom domain (bought via Cloudflare Registrar, DNS pointed at Render)
  with automatic, free SSL — no Cloudflare Tunnel needed.
- A GitHub Actions pipeline: the 4 existing CI workflows run first; only once
  **all four pass** does a final job call Render's Deploy Hook to trigger the
  actual deploy. Auto-Deploy-on-push is turned off in Render specifically so
  a raw push can't bypass CI.
- Zero-downtime swap and automatic rollback on a failed health check —
  handled natively by Render (via its Health Check Path setting), so there's
  no custom SSH/bash swap script to write or maintain.
- Cost: **US$0/month** on Render's free tier (one caveat: the free tier spins
  down after ~15 min idle and cold-starts in ~30–50s on the next request),
  plus ~US$10/year for the domain.

---

## Phase 1 — Render account and service

### 1.1 Create a Render account and connect GitHub
**Responsible: You**

1. Sign up at `render.com` (GitHub OAuth is the easiest path).
2. When prompted to connect a GitHub account/repos, authorize access to
   `sefop/sefop-python-advanced` (you can scope it to just this repo rather
   than all repos).

### 1.2 Create the Web Service
**Responsible: You**

1. Dashboard → *New* → *Web Service*.
2. Select the `sefop-python-advanced` repo.
3. Render should auto-detect the `Dockerfile` and offer **Docker** as the
   environment — confirm that's selected (not a buildpack).
4. Name: `sefop-web`. Region: whichever is closest to your users. Instance
   Type: **Free**.
5. Leave build/start commands blank — the `Dockerfile`'s own `CMD` already
   handles this.

### 1.3 Set the health check path
**Responsible: You**

Settings → *Health Check Path* → `/health`.

This is the setting that makes Render's own deploys zero-downtime: it won't
cut traffic over to a new deploy (and will treat it as failed) unless this
path returns 200. This is doing the job the custom swap/rollback script would
have done on a self-managed VM — for free, built in.

### 1.4 Turn off Auto-Deploy
**Responsible: You**

Settings → *Auto-Deploy* → **Off**.

Important: Render's default is to redeploy on every push automatically. We
don't want that — we want deploys gated on all 4 CI checks passing first.
Turning this off means the only thing that can trigger a deploy is the Deploy
Hook we wire up in Phase 3.

### 1.5 Copy the Deploy Hook URL
**Responsible: You**

Settings → *Deploy Hook* → copy the URL. Treat it as a secret (anyone with
this URL can trigger a deploy) — don't paste it anywhere public or commit it
to the repo. You'll hand it to Claude Code in Phase 3 to store as a GitHub
secret.

### 1.6 (Optional) Environment variables
**Responsible: You**

Environment tab → only needed if you want to override `SOLVER_NAME` (defaults
to `google_scip` if unset — see `src/startup.py`). Skip this unless you have
a reason to change it.

---

## Phase 2 — Domain

### 2.1 Buy the domain
**Responsible: You**

Cloudflare dashboard → Domain Registration → register a domain (~US$10/year,
at-cost pricing).

### 2.2 Add the custom domain in Render
**Responsible: You**

Service → Settings → *Custom Domains* → add `sefop.<yourdomain>`. Render will
show you the exact DNS record to create (typically a CNAME to something like
`sefop-web-xxxx.onrender.com`).

### 2.3 Create that DNS record in Cloudflare
**Responsible: You**

Cloudflare dashboard → DNS → add the record exactly as Render specified.
**Set the proxy status to "DNS only" (grey cloud), not "Proxied" (orange
cloud)** — Render issues its own Let's Encrypt certificate and needs to see
the real DNS target to verify domain ownership and provision SSL; Cloudflare's
proxy can interfere with that verification.

### 2.4 Wait for SSL
**Responsible: You** (just watching)

Render auto-provisions the certificate once DNS resolves — usually minutes,
occasionally up to an hour. Confirm the domain shows "Verified" with SSL
issued in the Render dashboard before moving on.

---

## Phase 3 — CD pipeline (this repo)

**Responsible: Claude Code** (all committed to the repo)

1. Add a `workflow_call:` trigger to each of the 4 existing CI workflow files
   (`ci-code-style.yml`, `ci-unit-tests.yml`, `ci-integration-tests.yml`,
   `ci-docker-build.yml`), alongside their existing `push`/`pull_request`
   triggers — so a parent workflow can run them as jobs with real
   dependencies (`needs`), not a race against separate `workflow_run` events.
2. Add `.github/workflows/cd-deploy.yml`:
   - Trigger: `push: branches: [main]`.
   - Jobs `code-style`, `unit-tests`, `integration-tests`, `docker-build`,
     each via `uses: ./.github/workflows/ci-*.yml`.
   - `deploy` job (`needs` all four above): a single step —
     `curl --fail -X POST "$RENDER_DEPLOY_HOOK_URL"`. That's the entire
     deploy step. No image build, no push, no SSH — Render does the build,
     the zero-downtime swap, and the health-check-gated rollback itself once
     the hook fires.
3. Set the GitHub secret via CLI (so the hook URL is never pasted into a
   browser form or committed): `gh secret set RENDER_DEPLOY_HOOK_URL` — you
   provide the URL from step 1.5, Claude Code runs the command.
4. Commit via a PR so the new/changed workflow files themselves pass CI
   before merging to `main`.

---

## Phase 4 — First deploy and verification

**Responsible: Claude Code**, with you watching Render's dashboard

1. Merge the PR from Phase 3 to `main`.
2. Watch `cd-deploy.yml` in the Actions tab: 4 CI jobs green → `deploy` job
   fires the hook.
3. Switch to the Render dashboard — a new deploy should start automatically
   right after the hook fires. Confirm it reaches **Live**.
4. Confirm `https://sefop.<yourdomain>/health` returns 200.
5. Test the rollback path for real: push a change that passes existing CI
   (it doesn't touch tests or the Dockerfile) but breaks `/health` at
   runtime — e.g. temporarily make the health handler return a 500. Confirm
   Render refuses to cut traffic over to the broken deploy and the site keeps
   serving the last good version. This is the live proof that "deploy only
   promotes on a healthy check" actually holds, not just that it's configured.

---

## Quick reference: who does what, in order

| # | Step | Responsible |
|---|------|-------------|
| 1.1 | Create Render account, connect GitHub | You |
| 1.2 | Create the Web Service (Docker) | You |
| 1.3 | Set Health Check Path to `/health` | You |
| 1.4 | Turn off Auto-Deploy | You |
| 1.5 | Copy the Deploy Hook URL | You |
| 1.6 | (Optional) env vars | You |
| 2.1 | Buy domain via Cloudflare Registrar | You |
| 2.2 | Add custom domain in Render | You |
| 2.3 | Add DNS record in Cloudflare (DNS-only) | You |
| 2.4 | Wait for SSL to verify | You |
| 3 | Add `workflow_call` to 4 CI workflows | Claude Code |
| 3 | Add `cd-deploy.yml` orchestrator + deploy job | Claude Code |
| 3 | Set `RENDER_DEPLOY_HOOK_URL` secret | Claude Code (via `gh secret set`) |
| 3 | Open PR, merge once CI passes | Claude Code |
| 4 | Merge, watch pipeline, verify, test rollback | Claude Code + You |
