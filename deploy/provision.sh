#!/usr/bin/env bash
# Provision the auto48 production host (Ubuntu 24.04).
#
# Installs the data layer (Docker: Postgres+PostGIS, Redis, MinIO) and the
# public edge (nginx + certbot), locks the firewall to 22/80/443, and generates
# on-box secrets. Idempotent: safe to re-run. Does NOT deploy app code.
#
# Run from the directory containing this script and docker-compose.prod.yml:
#   sudo bash provision.sh
set -euo pipefail

APP_DIR=/opt/auto48
ENV_FILE="$APP_DIR/.env"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

log "apt: base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg openssl ufw nginx

log "Docker Engine + compose plugin (official repo)"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
usermod -aG docker ubuntu || true

log "certbot (snap — the supported install path)"
if ! command -v certbot >/dev/null; then
  apt-get install -y -qq snapd
  snap install core >/dev/null 2>&1 || true
  snap install --classic certbot
  ln -sf /snap/bin/certbot /usr/bin/certbot
fi

log "Firewall: allow OpenSSH + 80/443, deny the rest"
ufw allow OpenSSH       >/dev/null
ufw allow 'Nginx Full'  >/dev/null
ufw --force enable

log "App dir + secrets ($ENV_FILE)"
mkdir -p "$APP_DIR"
cp "$SRC_DIR/docker-compose.prod.yml" "$APP_DIR/docker-compose.prod.yml"
if [[ ! -f "$ENV_FILE" ]]; then
  gen() { openssl rand -base64 24 | tr -d '/+=' | head -c 32; }
  PG_PW=$(gen); REDIS_PW=$(gen); MINIO_PW=$(gen); JWT=$(openssl rand -hex 32)
  cat > "$ENV_FILE" <<EOF
# auto48 production secrets — generated $(date -u +%FT%TZ). DO NOT COMMIT.
# --- data layer (consumed by docker-compose.prod.yml) ---
POSTGRES_USER=auto48
POSTGRES_PASSWORD=${PG_PW}
POSTGRES_DB=auto48
REDIS_PASSWORD=${REDIS_PW}
MINIO_ROOT_USER=auto48
MINIO_ROOT_PASSWORD=${MINIO_PW}
S3_BUCKET=auto48-media
# --- application config (AUTO48_*), used when app code is deployed ---
AUTO48_ENVIRONMENT=production
AUTO48_DATABASE_URL=postgresql+asyncpg://auto48:${PG_PW}@127.0.0.1:5432/auto48
AUTO48_REDIS_URL=redis://:${REDIS_PW}@127.0.0.1:6379/0
AUTO48_S3_ENDPOINT=http://127.0.0.1:9000
AUTO48_S3_ACCESS_KEY=auto48
AUTO48_S3_SECRET_KEY=${MINIO_PW}
AUTO48_S3_BUCKET=auto48-media
AUTO48_JWT_SECRET=${JWT}
EOF
  chmod 600 "$ENV_FILE"
  echo "  generated new secrets"
else
  echo "  $ENV_FILE exists — left untouched"
fi

log "nginx site"
cp "$SRC_DIR/nginx/auto48.conf" /etc/nginx/sites-available/auto48.conf
ln -sf /etc/nginx/sites-available/auto48.conf /etc/nginx/sites-enabled/auto48.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

log "Start data layer"
cd "$APP_DIR"
docker compose -f docker-compose.prod.yml --env-file .env pull
docker compose -f docker-compose.prod.yml --env-file .env up -d

log "Done. Listening sockets (expect only sshd:22, nginx:80/443 on public iface):"
ss -tlnp | grep -E 'LISTEN' || true
echo
echo "PostGIS available?"; docker compose -f docker-compose.prod.yml exec -T db \
  psql -U auto48 -d auto48 -tAc "SELECT 'PostGIS ' || extversion FROM pg_extension WHERE extname='postgis';" || true
