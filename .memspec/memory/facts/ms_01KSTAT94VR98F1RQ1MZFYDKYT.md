---
id: ms_01KSTAT94VR98F1RQ1MZFYDKYT
type: fact
state: active
confidence: 0.8
created: '2026-05-29T16:59:24.700Z'
source: unknown
tags:
  - deploy
  - infra
  - ssh
  - production
decay_after: '2026-08-27T16:53:21.261Z'
corrects: ms_01KSTAF67CJRTE7PNTNWHJXW7M
---
# Production deploy: VPS 178.105.234.239 (Ubuntu), SSH user ubuntu, key auto48_deploy

auto48 prod server is 178.105.234.239 (hostname ubuntu-4gb-nbg1-2, Hetzner Cloud 4GB Nuremberg/nbg1), Ubuntu 24.04 LTS, SSH user 'ubuntu'. Auth via ed25519 deploy key ~/.ssh/auto48_deploy (private; not in repo); pubkey installed in server authorized_keys and documented in docs/deployment.md. SSH alias 'auto48-prod' in ~/.ssh/config. Verified reachable: TCP/22 open, key login works; ICMP ping filtered. See docs/deployment.md.
