#!/usr/bin/env bash
# Deploy the auto48 application onto an already-provisioned host (see provision.sh).
#
# Installs the backend into a venv, runs Alembic migrations, builds the Nuxt
# frontend, and installs+starts three systemd units (api, worker, web). The data
# layer (Postgres/Redis/MinIO) and nginx/TLS must already be up. Idempotent:
# safe to re-run for redeploys.
#
# The app code is shipped separately as a clean `git archive HEAD` export to
# /opt/auto48/app (so uncommitted work never reaches prod), then:
#   sudo bash /opt/auto48/app/deploy/deploy-app.sh
set -euo pipefail

APP_DIR=/opt/auto48/app
VENV=/opt/auto48/venv
ENV_FILE=/opt/auto48/.env
NODE_MAJOR=22

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE — run provision.sh first." >&2; exit 1; }

log "Service user 'auto48'"
id auto48 &>/dev/null || useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" auto48
chown -R auto48:auto48 /opt/auto48/app
# .env keeps its root-only perms; systemd reads it before dropping privileges.
chown root:root "$ENV_FILE"; chmod 600 "$ENV_FILE"

log "Swap (insurance against nuxt build OOM on 4GB)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

log "Python venv + backend install"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3-venv python3-dev >/dev/null
[[ -d "$VENV" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q "$APP_DIR"
chown -R auto48:auto48 "$VENV"

log "Database migrations (alembic upgrade head)"
set -a; . "$ENV_FILE"; set +a
( cd "$APP_DIR" && "$VENV/bin/alembic" upgrade head )
( cd "$APP_DIR" && "$VENV/bin/alembic" check ) || \
  echo "WARNING: alembic check reports drift — review before relying on the schema."

log "Node ${NODE_MAJOR} (NodeSource)"
if ! command -v node >/dev/null || [[ "$(node -v | grep -oE '[0-9]+' | head -1)" -lt "$NODE_MAJOR" ]]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi

log "Frontend build (npm ci + nuxt build)"
runuser -u auto48 -- bash -lc "cd $APP_DIR/frontend && HOME=$APP_DIR npm ci --no-audit --no-fund && HOME=$APP_DIR npm run build"

log "systemd units"
cp "$APP_DIR"/deploy/systemd/auto48-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now auto48-api.service auto48-worker.service auto48-web.service
systemctl restart auto48-api.service auto48-worker.service auto48-web.service

log "Smoke tests"
sleep 4
for u in auto48-api auto48-worker auto48-web; do
  printf '  %-16s %s\n' "$u" "$(systemctl is-active $u)"
done
echo "  GET :8000/health      -> $(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health || echo FAIL)"
echo "  GET :8000/v1/listings -> $(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/v1/listings || echo FAIL)"
echo "  GET :3000/ (nuxt)     -> $(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ || echo FAIL)"
echo
echo "Done. Public: https://kekec.ee"
