# Deployment

> Operational deployment info for auto48. Secrets (private keys, env values) live
> outside the repo — never commit them.

## Production server

| | |
|---|---|
| **Host (IP)** | `178.105.234.239` |
| **Hostname** | `ubuntu-4gb-nbg1-2` |
| **Provider** | Hetzner Cloud — 4 GB instance, Nuremberg (nbg1) |
| **OS** | Ubuntu 24.04 LTS (kernel 6.8) |
| **SSH user** | `ubuntu` |
| **Auth** | SSH key pair (`ed25519`), password auth disabled |

> Verified reachable: TCP/22 open and key-based login succeeds. ICMP ping is
> filtered (expected) — use the SSH check below to confirm reachability.

### SSH access

A dedicated deploy key pair was generated on the operator workstation:

- Private key: `~/.ssh/auto48_deploy` (never leaves the workstation, not in git)
- Public key:  `~/.ssh/auto48_deploy.pub`

Public key (install in the server's `~ubuntu/.ssh/authorized_keys`):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJDFQUtZUqWRfcMktU+iA+3s7ezV6nhQbBi+F5ONztXl auto48-deploy@178.105.234.239
```

A convenience alias is configured in `~/.ssh/config`:

```sshconfig
Host auto48-prod
    HostName 178.105.234.239
    User ubuntu
    IdentityFile ~/.ssh/auto48_deploy
    IdentitiesOnly yes
```

Connect with:

```bash
ssh auto48-prod
```

### First-time key install

If the public key is not yet on the server, install it once (using an existing
credential — console/password or another authorized key):

```bash
ssh-copy-id -i ~/.ssh/auto48_deploy.pub ubuntu@178.105.234.239
```

Then harden `/etc/ssh/sshd_config` on the server: `PasswordAuthentication no`,
`PermitRootLogin no`, and `sudo systemctl reload ssh`.

## Provisioned components

Provision the box with `deploy/provision.sh` (idempotent; recipe in repo, secrets
generated on-box). It installs the data layer via Docker Compose — mirroring the dev
`docker-compose.yml` for parity — plus a host nginx/certbot edge, and locks the firewall.

| Component | Version | Where | Exposure |
|---|---|---|---|
| Docker Engine + Compose | 29.x / v5.x | host (apt, official repo) | — |
| PostgreSQL + PostGIS | **17 / 3.5** | container `auto48-db-1` | `127.0.0.1:5432` |
| Redis | **8** (alpine, `requirepass`) | container `auto48-redis-1` | `127.0.0.1:6379` |
| MinIO (S3 object store) | latest | container `auto48-minio-1` | `127.0.0.1:9000` (api) / `:9001` (console) |
| nginx | 1.24 | host | public `:80` (`:443` after TLS) |
| certbot | 5.x (snap) | host | — |

**Security:** every data service binds to `127.0.0.1` only — never a public interface.
The public edge is nginx (`ufw` allows just `22/80/443`). Verified externally: only 22 and
80 are reachable; 5432/6379/9000 are blocked. Redis requires a password.

### Secrets

`/opt/auto48/.env` (root-only, `chmod 600`, **never committed**) holds generated
Postgres/Redis/MinIO passwords, a JWT secret, and the `AUTO48_*` app config (DSNs point at
`127.0.0.1`). Regenerated only if the file is absent — re-running `provision.sh` won't clobber it.

### Managing the data stack

```bash
ssh auto48-prod
cd /opt/auto48
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs -f db
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d   # apply changes
```

## TLS (Let's Encrypt)

Done — `https://kekec.ee` serves a publicly-trusted Let's Encrypt certificate
(`kekec.ee` + `www.kekec.ee`, ~90-day profile). `deploy/obtain-cert.sh` obtains it via
the `http-01` webroot challenge (`/var/www/certbot`, served by the `acme.conf` nginx
snippet) and swaps nginx to `deploy/nginx/auto48-tls.conf`. The certbot snap timer renews
automatically; a deploy-hook (`/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`)
reloads nginx after each renewal. nginx redirects `http://` and `www.` → `https://kekec.ee`.

> An earlier bare-IP certificate for `178.105.234.239` was issued first (Let's Encrypt's
> **`shortlived` ~6-day profile**, required for IP certs) — kept as a fallback lineage.
> Verify: `ssh auto48-prod 'sudo certbot certificates'`.

To re-run on a fresh box or new domain: `sudo bash deploy/obtain-cert.sh` (edit the
`server_name`/cert paths + the `-d` domains, or `--ip-address`, as needed).

## Application (deployed)

`https://kekec.ee` runs **Phase 1a** (6 routers; pre-1b commit `08df477` plus the arq
worker fix `630af45`). Deployed by `deploy/deploy-app.sh` from a clean `git archive`
export to `/opt/auto48/app`, installed into `/opt/auto48/venv`. Three systemd units:

| Unit | Runs | Bind |
|---|---|---|
| `auto48-api` | uvicorn `auto48.main:app` (2 workers) | `127.0.0.1:8000` |
| `auto48-worker` | arq `auto48.workers.images.WorkerSettings` | → Redis |
| `auto48-web` | Nuxt SSR (`node .output/server/index.mjs`) | `127.0.0.1:3000` |

Service user `auto48`; secrets via `EnvironmentFile=/opt/auto48/.env`. Migrations applied
(`alembic upgrade head` → `abd0726bfcd2`, 8 tables). Verified: `/health`, `/v1/listings`,
and the SSR homepage all 200 over HTTPS; worker connected to Redis.

```bash
ssh auto48-prod 'sudo systemctl status auto48-api auto48-worker auto48-web'
ssh auto48-prod 'sudo journalctl -u auto48-api -f'
```

### Redeploy

Re-ship the export and re-run (idempotent):
```bash
git archive <ref> | ssh auto48-prod 'sudo tar -x -C /opt/auto48/app'
ssh auto48-prod 'sudo bash /opt/auto48/app/deploy/deploy-app.sh'
```
> A clean `git archive 08df477` (1a) lacks the worker fix `630af45` — ship the fixed
> `src/auto48/workers/images.py` on top, or deploy a ref that includes it.

### Notes / follow-ups

- `alembic check` reports benign "drift" — the PostGIS image's Tiger-geocoder tables
  (`zcta5`, `cousub`, `pagc_rules`, …) aren't in the ORM. Add an `include_object` filter
  in `alembic/env.py` so `check`/autogenerate ignore non-app tables.
- **Migrations**: always run **Alembic** as a deploy step — never `create_all` outside `local`.
- SSR fetches currently hairpin through `https://kekec.ee`; could point server-side calls
  at `http://127.0.0.1:8000` later.

> **Capacity note:** 4 GB / 2 vCPU runs Postgres + Redis + MinIO + nginx (and soon
> FastAPI + Nuxt SSR) on one box — fine pre-launch; revisit before scaling traffic.
