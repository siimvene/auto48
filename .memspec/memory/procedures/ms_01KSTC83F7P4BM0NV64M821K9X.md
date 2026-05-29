---
id: ms_01KSTC83F7P4BM0NV64M821K9X
type: procedure
state: active
confidence: 0.7
created: '2026-05-29T17:24:26.215Z'
source: claude
tags:
  - deploy
  - procedure
  - infra
decay_after: '2026-08-27T17:24:26.216Z'
---
# Provision/deploy prod server (deploy/ scripts)

Recipe lives in repo deploy/. (1) scp deploy/ to server home (NOT into existing dir — scp -r nests). (2) sudo bash provision.sh: installs Docker+compose, nginx, certbot (snap), ufw 22/80/443, generates /opt/auto48/.env secrets, brings up docker-compose.prod.yml data stack. (3) sudo bash obtain-cert.sh: http-01 webroot cert + swap nginx to auto48-tls.conf + renewal reload hook. For a domain edit -d flags + server_name/cert paths; for bare IP use --ip-address + --preferred-profile shortlived. Manage stack: cd /opt/auto48 && sudo docker compose -f docker-compose.prod.yml ps. STILL TODO to deploy app: get code on box, python3.12 venv + pip install, alembic upgrade head against prod DB, uvicorn systemd unit, install Node + nuxt build + SSR service.
