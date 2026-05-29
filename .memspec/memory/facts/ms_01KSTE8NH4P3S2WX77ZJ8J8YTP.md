---
id: ms_01KSTE8NH4P3S2WX77ZJ8J8YTP
type: fact
state: active
confidence: 0.8
created: '2026-05-29T17:59:41.861Z'
source: unknown
tags:
  - deploy
  - infra
  - tls
  - nginx
  - production
decay_after: '2026-08-27T17:24:26.099Z'
corrects: ms_01KSTC83BHYWEE87NRF0CRF11M
---
# Prod provisioned: Docker data stack + nginx TLS, domain kekec.ee

auto48 prod (178.105.234.239 / https://kekec.ee) fully deployed for Phase 1a. Docker data layer (PostgreSQL+PostGIS 17, Redis 8 w/ password, MinIO) bound to 127.0.0.1; host nginx + Let's Encrypt 90-day domain cert (kekec.ee, www->apex redirect). App in /opt/auto48/app (clean git-archive export of 1a commit 08df477 + arq worker fix 630af45), venv /opt/auto48/venv, secrets /opt/auto48/.env (root 600). Three systemd units: auto48-api (uvicorn auto48.main:app :8000), auto48-worker (arq auto48.workers.images.WorkerSettings), auto48-web (Nuxt SSR :3000), all User=auto48, EnvironmentFile=.env. DB migrated to abd0726bfcd2 (8 tables). 1b deliberately excluded per user. ufw 22/80/443. See docs/deployment.md.
