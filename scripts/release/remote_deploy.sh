#!/usr/bin/env bash
# Runs as the dedicated deploy user, after GitHub Environment approval.
# Neither a failed migration nor a failed smoke check automatically restores DB.
set -Eeuo pipefail
umask 077

[[ $# == 3 ]] || { echo "Expected SHA, API digest, frontend digest" >&2; exit 2; }
sha="$1"
api_image="$2"
frontend_image="$3"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid commit SHA" >&2; exit 2; }
digest_regex='^ghcr.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'
[[ "$api_image" =~ $digest_regex && "$frontend_image" =~ $digest_regex ]] || {
  echo "Only immutable GHCR image digests are allowed" >&2; exit 2;
}
# No command in this script may drain its source. The script itself is run
# from disk; also disconnect stdin defensively.
exec </dev/null

root="$HOME/SciConnect"
release="$root/releases/$sha"
env_file="$root/.env.production"
state="$root/release-state"
[[ -r "$env_file" && -f "$release/compose.prod.yaml" &&
   -f "$release/compose.release.yaml" && -f "$release/Caddyfile" ]] || {
  echo "Production env or verified release bundle missing" >&2; exit 1;
}
mkdir -p "$state" "$root/backups"
chmod 700 "$state" "$root/backups"
exec 9>"$state/deploy.lock"
flock -n 9 || { echo "Another release or rollback holds the server lock" >&2; exit 1; }

export SCICONNECT_API_IMAGE="$api_image" SCICONNECT_FRONTEND_IMAGE="$frontend_image"
compose=(docker compose -p sciconnect --project-directory "$release" \
  -f "$release/compose.prod.yaml" -f "$release/compose.release.yaml" \
  --env-file "$env_file")
"${compose[@]}" config --quiet
db_container="$("${compose[@]}" ps -q db)"
[[ -n "$db_container" ]] || {
  echo "Database is not running. Bootstrap the stack manually first." >&2; exit 1;
}
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$db_container")" == "healthy" ]] || {
  echo "Database must be healthy before migration" >&2; exit 1;
}

# Pull first so failures in registry/credentials cannot alter the database.
"${compose[@]}" pull api frontend
# Only one Alembic head is supported by this release gate.
heads="$("${compose[@]}" run --rm --no-deps --entrypoint alembic api heads)"
expected_revision="$(printf '%s\n' "$heads" | awk 'NF {print $1}')"
[[ "$expected_revision" =~ ^[a-zA-Z0-9_]+$ ]] || {
  echo "Expected exactly one valid Alembic head, got: $heads" >&2; exit 1;
}

# Refuse a backup if the local disk cannot hold a conservative estimate.
# This fails CLOSED rather than consuming Postgres' free disk while dumping.
db_bytes="$("${compose[@]}" exec -T db sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT pg_database_size(current_database())"' \
  | tr -d '\r\n')"
free_kb="$(df -Pk "$root/backups" | awk 'NR==2 {print $4}')"
[[ "$db_bytes" =~ ^[0-9]+$ && "$free_kb" =~ ^[0-9]+$ ]] || {
  echo "Could not determine database size or available backup storage" >&2; exit 1;
}
minimum_bytes=$((db_bytes * 2 + 512 * 1024 * 1024))
((free_kb * 1024 > minimum_bytes)) || {
  echo "Insufficient free disk for pre-migration backup; offload old verified dumps" >&2
  exit 1
}

# Never use an unverified partial backup. Keep it outside the release directory.
backup="$root/backups/pre-${sha}-$(date -u +%Y%m%dT%H%M%SZ).dump"
partial="$backup.partial"
trap 'rm -f -- "$partial"' EXIT
"${compose[@]}" exec -T db sh -ec \
  'exec pg_dump -Fc --no-owner --no-acl -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$partial"
[[ -s "$partial" ]] || { echo "Empty database backup" >&2; exit 1; }
# Parse every data block, not just the TOC: pg_restore --list accepts
# a valid header plus a truncated body. This is not a substitute for a
# staging restore into a clean database, but rejects truncated archives.
"${compose[@]}" exec -T db pg_restore -f /dev/null < "$partial" >/dev/null
mv -- "$partial" "$backup"
sha256sum "$backup" > "$backup.sha256"
echo "Verified pre-migration backup: $backup"
echo "Do not restore a database automatically after migration; see docs/RELEASE.md"

# Migration is an explicit one-off container. New API starts with migrations
# disabled, avoiding repeated migrations during restarts or rollback.
"${compose[@]}" run --rm --no-deps --entrypoint alembic api upgrade head
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 180

# A healthy old container is not sufficient: verify the *running* images
# match the approved immutable digest references before promoting the SHA.
for service in api frontend; do
  cid="$("${compose[@]}" ps -q "$service")"
  [[ -n "$cid" ]] || { echo "Missing $service container" >&2; exit 1; }
  image_ref="$(docker inspect --format '{{.Config.Image}}' "$cid")"
  if [[ "$service" == api ]]; then expected_image="$api_image"
  else expected_image="$frontend_image"; fi
  [[ "$image_ref" == "$expected_image" ]] || {
    echo "Wrong running $service image; refusing to promote release" >&2; exit 1;
  }
done

# Read only the domain from the local env; never echo credentials to logs.
domain="$(sed -n 's/^SITE_DOMAIN=//p' "$env_file" | tail -n 1)"
domain="${domain%\"}"
domain="${domain#\"}"
[[ "$domain" =~ ^[a-zA-Z0-9.-]+$ ]] || {
  echo "Invalid SITE_DOMAIN in production env" >&2; exit 1;
}
healthy=false
for attempt in $(seq 1 15); do
  if curl --proto '=https' --tlsv1.2 -fsS --max-time 10 "https://$domain/" \
      >/dev/null 2>&1 &&
     curl --proto '=https' --tlsv1.2 -fsS --max-time 10 \
       "https://$domain/api/v1/health" >/dev/null 2>&1 &&
     curl --proto '=https' --tlsv1.2 -fsS --max-time 10 \
       "https://$domain/api/v1/catalog/institutions" >/dev/null 2>&1 &&
     "${compose[@]}" exec -T api python -c \
       'import json,sys,urllib.request; body=json.load(urllib.request.urlopen("http://localhost:8000/api/v1/health/database",timeout=10)); assert body["database"]=="ok" and body["migration"]==sys.argv[1]' \
       "$expected_revision" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 5
done
[[ "$healthy" == "true" ]] || {
  echo "Post-deploy smoke check failed; state not promoted." >&2
  echo "Backup: $backup; run operator-only rollback after checking migrations." >&2
  exit 1
}

if [[ -f "$state/current-release" ]]; then
  read -r current_sha current_api_image current_frontend_image < "$state/current-release"
  # Same source SHA may rebuild to DIFFERENT digests (mutable base images or
  # dependency ranges). Keep the old healthy pair as rollback unless the
  # *complete* release identity -- SHA and both digests -- is unchanged.
  if [[ "$current_sha" != "$sha" ||
        "$current_api_image" != "$api_image" ||
        "$current_frontend_image" != "$frontend_image" ]]; then
    cp -- "$state/current-release" "$state/previous-release"
  fi
fi
printf '%s %s %s\n' "$sha" "$api_image" "$frontend_image" > "$state/current-release.new"
mv -- "$state/current-release.new" "$state/current-release"
echo "Release healthy and recorded: $sha"
printf 'RELEASE_OK %s\n' "$sha"
