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

## Notes

- Database schema changes deploy via **Alembic** as an explicit deploy step
  (`alembic upgrade head`) — never `create_all` on startup outside `local`.
