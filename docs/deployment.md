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

### Not yet done (deploy step)

- **App code** (FastAPI + Nuxt) is not deployed yet — nginx upstreams `127.0.0.1:8000`
  (backend) and `:3000` (frontend) are configured and waiting. No app service unit,
  Python venv, or Node runtime exists on the box yet.
- **Migrations**: run **Alembic** as a deploy step (`alembic upgrade head`) — never
  `create_all` on startup outside `local`.

> **Capacity note:** 4 GB / 2 vCPU runs Postgres + Redis + MinIO + nginx (and soon
> FastAPI + Nuxt SSR) on one box — fine pre-launch; revisit before scaling traffic.
