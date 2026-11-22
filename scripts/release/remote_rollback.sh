#!/usr/bin/env bash
# Operator-only app rollback. Database migrations are NEVER automatically undone.
set -Eeuo pipefail
umask 077
[[ "${CONFIRM_DB_COMPATIBLE:-}" == "yes" ]] || {
  echo "Set CONFIRM_DB_COMPATIBLE=yes only after checking migration compatibility" >&2
  exit 1
}
choice="${1:-}"
[[ "$choice" == "current" || "$choice" == "previous" ]] || {
  echo "Usage: CONFIRM_DB_COMPATIBLE=yes bash remote_rollback.sh current|previous" >&2
  exit 2
}
root="$HOME/SciConnect"
state="$root/release-state"
file="$state/$choice-release"
[[ -r "$file" ]] || { echo "No recorded $choice release" >&2; exit 1; }
exec 9>"$state/deploy.lock"
flock -n 9 || { echo "Another release or rollback is in progress" >&2; exit 1; }

read -r sha api_image frontend_image < "$file"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
digest_regex='^ghcr.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'
[[ "$api_image" =~ $digest_regex && "$frontend_image" =~ $digest_regex ]] || exit 2
release="$root/releases/$sha"
[[ -f "$release/compose.prod.yaml" && -f "$release/compose.release.yaml" ]] || {
  echo "Old release bundle missing; cannot roll back" >&2; exit 1;
}

export SCICONNECT_API_IMAGE="$api_image" SCICONNECT_FRONTEND_IMAGE="$frontend_image"
compose=(docker compose -p sciconnect --project-directory "$release" \
  -f "$release/compose.prod.yaml" -f "$release/compose.release.yaml" \
  --env-file "$root/.env.production")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build --pull always --wait --wait-timeout 180
"${compose[@]}" exec -T api python -c \
  'import json,urllib.request; body=json.load(urllib.request.urlopen("http://localhost:8000/api/v1/health/database",timeout=10)); assert body["database"]=="ok" and body["migration"]'
echo "App rollback started: $sha. Verify public HTTPS and data before updating release state."

# Promote only after the operator has confirmed external checks. This keeps
# current-release as the last verified release if a rollback partly fails.
