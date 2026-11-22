#!/usr/bin/env bash
# Rehearse a CUSTOM-format backup in an ISOLATED disposable PostgreSQL container.
# No ports, volumes, external credentials, or production database connections.
set -Eeuo pipefail
[[ $# == 1 && -s "$1" ]] || {
  echo "Usage: bash scripts/release/restore_drill.sh path/to/backup.dump" >&2
  exit 2
}
backup="$1"
container="sciconnect-restore-drill-$$-$RANDOM"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker run -d --rm --name "$container" --network none \
  -e POSTGRES_PASSWORD=local-drill-only postgres:17-alpine >/dev/null
ready=false
for attempt in $(seq 1 30); do
  # The official image also runs a short-lived initialization server.
  # Wait until PID 1 has exec'd the FINAL postgres process before restoring.
  # This works with --network none, where TCP loopback may not be configured.
  if docker exec "$container" sh -ec \
      '[ "$(cat /proc/1/comm)" = postgres ] && pg_isready -U postgres' \
      >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
[[ "$ready" == "true" ]] || { echo "Disposable PostgreSQL did not start" >&2; exit 1; }
docker exec -i "$container" pg_restore -U postgres -d postgres \
  --exit-on-error --no-owner --no-privileges < "$backup"
test "$(docker exec "$container" psql -U postgres -d postgres \
  -Atqc "SELECT to_regclass('public.institutions') IS NOT NULL")" == "t"
echo "Restore drill passed in isolated PostgreSQL 17. Production was not accessed."
