#!/usr/bin/env bash
# Obtain a Let's Encrypt TLS certificate for the bare IP address and switch
# nginx to HTTPS. Uses the "shortlived" profile (~6-day certs) — the only
# profile Let's Encrypt issues IP-address certificates under — with the
# http-01 challenge served from the nginx webroot.
#
# certbot's nginx installer does NOT yet support IP certs, so this obtains the
# cert with `certonly --webroot` and wires it into nginx by hand, then installs
# a renewal deploy-hook to reload nginx.
#
#   sudo bash obtain-cert.sh [--staging]
set -euo pipefail

IP=178.105.234.239
WEBROOT=/var/www/certbot
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING="${1:-}"

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

# 1. ACME webroot + snippet must exist and be served on :80 (auto48.conf).
mkdir -p "$WEBROOT/.well-known/acme-challenge"
install -m 0644 /dev/stdin /etc/nginx/snippets/acme.conf <<'EOF'
location ^~ /.well-known/acme-challenge/ {
    root /var/www/certbot;
    default_type "text/plain";
}
EOF
cp "$SRC_DIR/nginx/auto48.conf" /etc/nginx/sites-available/auto48.conf
nginx -t && systemctl reload nginx

# 2. Issue the IP certificate (shortlived profile, http-01 via webroot).
EMAIL_FLAG="--register-unsafely-without-email"
certbot certonly \
  ${STAGING:+--staging} \
  --non-interactive --agree-tos $EMAIL_FLAG \
  --preferred-profile shortlived \
  --webroot --webroot-path "$WEBROOT" \
  --ip-address "$IP"

# 3. Swap nginx to the TLS config (now that the cert exists) and reload.
#    Write LE's recommended TLS options + dhparams if absent.
if [[ ! -f /etc/letsencrypt/options-ssl-nginx.conf ]]; then
  cat > /etc/letsencrypt/options-ssl-nginx.conf <<'EOF'
ssl_session_cache shared:le_nginx_SSL:10m;
ssl_session_timeout 1440m;
ssl_session_tickets off;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
EOF
fi
[[ -f /etc/letsencrypt/ssl-dhparams.pem ]] || \
  openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048

cp "$SRC_DIR/nginx/auto48-tls.conf" /etc/nginx/sites-available/auto48.conf
nginx -t && systemctl reload nginx

# 4. Reload nginx automatically on every future renewal (6-day certs renew often).
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

echo
echo "Done. Certificate:"
certbot certificates 2>/dev/null | grep -E "Certificate Name|Expiry|Domains|Serial" || true
