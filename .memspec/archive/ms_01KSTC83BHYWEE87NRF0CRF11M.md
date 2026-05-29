---
id: ms_01KSTC83BHYWEE87NRF0CRF11M
type: fact
state: corrected
confidence: 0.7
created: '2026-05-29T17:24:26.097Z'
source: claude
tags:
  - deploy
  - infra
  - tls
  - nginx
  - production
decay_after: '2026-08-27T17:24:26.099Z'
corrected_by: ms_01KSTE8NH4P3S2WX77ZJ8J8YTP
---
# Prod provisioned: Docker data stack + nginx TLS, domain kekec.ee

auto48 prod (178.105.234.239) is provisioned via deploy/ recipe: Docker Compose data layer (PostgreSQL+PostGIS 17/3.5, Redis 8 w/ password, MinIO) all bound to 127.0.0.1; host nginx reverse proxy + Let's Encrypt TLS. Public domain is https://kekec.ee (+ www->apex redirect); 90-day domain cert. An earlier bare-IP cert used LE shortlived 6-day profile (IP certs require it). Secrets in /opt/auto48/.env (root-only, gitignored). ufw allows 22/80/443 only. APP CODE NOT YET DEPLOYED — no app systemd unit, no Node runtime, no venv on box; nginx upstreams :8000 (FastAPI) and :3000 (Nuxt) wait. See docs/deployment.md.
