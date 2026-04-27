#!/usr/bin/env sh
# Ephemeral TLS for container non-loopback binds (e.g. Akash) when the
# operator has not mounted XION_TLS_* material. Production operators should
# replace this with real certs and paths.
set -e

host="${XION_API_HOST:-127.0.0.1}"
cert="${XION_TLS_CERT_PATH:-}"
key="${XION_TLS_KEY_PATH:-}"

needs_tls=0
case "$host" in
  127.0.0.1|localhost|::1) needs_tls=0 ;;
  *) needs_tls=1 ;;
esac

if [ "$needs_tls" -eq 1 ]; then
  if [ -n "$cert" ] && [ ! -f "$cert" ]; then
    echo "State-of-Xion: XION_TLS_CERT_PATH is set but not a readable file: $cert" >&2
    exit 1
  fi
  if [ -n "$key" ] && [ ! -f "$key" ]; then
    echo "State-of-Xion: XION_TLS_KEY_PATH is set but not a readable file: $key" >&2
    exit 1
  fi
  have=0
  if [ -n "$cert" ] && [ -n "$key" ] && [ -f "$cert" ] && [ -f "$key" ]; then
    have=1
  fi
  if [ "$have" -eq 0 ]; then
    if [ "${XION_AKASH_EPHEMERAL_TLS:-1}" = "0" ]; then
      echo "State-of-Xion: non-loopback bind requires TLS files or XION_AKASH_EPHEMERAL_TLS=1." >&2
      exit 1
    fi
    dir="/var/lib/xion/akash-tls"
    mkdir -p "$dir"
    if [ ! -f "$dir/cert.pem" ]; then
      openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$dir/key.pem" \
        -out "$dir/cert.pem" \
        -days 30 \
        -subj "/CN=xion-relay-akash-ephemeral" >/dev/null 2>&1
    fi
    export XION_TLS_CERT_PATH="$dir/cert.pem"
    export XION_TLS_KEY_PATH="$dir/key.pem"
  fi
fi

exec xion-orchestrator-api "$@"
